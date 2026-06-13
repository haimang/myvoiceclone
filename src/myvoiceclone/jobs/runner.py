import sqlite3
import logging
import time
from typing import Dict, Any, Optional
from myvoiceclone.domain.entities import Job
from myvoiceclone.domain.states import JobStatus
from myvoiceclone.storage.repositories import JobRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.jobs.events import write_job_event, write_step_event

# Pipeline step imports
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.pipelines.diarize import run_diarize
from myvoiceclone.pipelines.slice import run_slice
from myvoiceclone.pipelines.clean import run_clean
from myvoiceclone.pipelines.transcribe import run_transcribe
from myvoiceclone.pipelines.score import run_score
from myvoiceclone.pipelines.train import run_train_sovits

# Adapter imports
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter
from myvoiceclone.adapters.training.sovits_adapter import SovitsAdapter

logger = logging.getLogger("myvoiceclone.jobs.runner")

class JobRunner:
    def __init__(
        self,
        conn: sqlite3.Connection,
        artifact_store: ArtifactStore,
        ffmpeg_adapter: Optional[Any] = None,
        pyannote_adapter: Optional[Any] = None,
        demucs_adapter: Optional[Any] = None,
        whisper_adapter: Optional[Any] = None,
        sovits_adapter: Optional[Any] = None
    ):
        self.conn = conn
        self.repo = JobRepository(conn)
        self.artifact_store = artifact_store
        
        if ffmpeg_adapter is None:
            from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
            ffmpeg_adapter = FFmpegAdapter()
        self.ffmpeg_adapter = ffmpeg_adapter
        
        if pyannote_adapter is None:
            from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
            pyannote_adapter = PyannoteAdapter()
        self.pyannote_adapter = pyannote_adapter
        
        if demucs_adapter is None:
            from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
            demucs_adapter = DemucsAdapter()
        self.demucs_adapter = demucs_adapter
        
        if whisper_adapter is None:
            from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter
            whisper_adapter = WhisperAdapter()
        self.whisper_adapter = whisper_adapter
        
        if sovits_adapter is None:
            from myvoiceclone.adapters.training.sovits_adapter import SovitsAdapter
            sovits_adapter = SovitsAdapter()
        self.sovits_adapter = sovits_adapter

    def run(self, job_id: str) -> None:
        job = self.repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
            
        old_status = job.status
        job.status = JobStatus.RUNNING.value
        self.repo.save(job)
        write_job_event(self.conn, job_id, "start", old_status, JobStatus.RUNNING.value, "Job started execution")
        self.conn.commit()
        
        try:
            if job.name == "preprocess_all":
                self._execute_preprocess_all(job)
            elif job.name == "ingest":
                self._execute_ingest(job)
            elif job.name == "train_sovits":
                self._execute_train_sovits(job)
            # V16 fix: per-step dispatch for individual preprocess steps
            # Enables step-level retry without re-running the entire chain
            elif job.name == "diarize":
                self._execute_step_diarize(job)
            elif job.name == "slice":
                self._execute_step_slice(job)
            elif job.name == "clean":
                self._execute_step_clean(job)
            elif job.name == "transcribe":
                self._execute_step_transcribe(job)
            elif job.name == "score":
                self._execute_step_score(job)
            elif job.name == "curate":
                self._execute_step_curate(job)
            elif job.name == "infer_real":
                self._execute_infer_real(job)
            elif job.name == "eval_first_test":
                self._execute_eval_first_test(job)
            else:
                raise ValueError(f"Unsupported job type: {job.name}")
                
            job.status = JobStatus.COMPLETED.value
            self.repo.save(job)
            write_job_event(
                self.conn,
                job_id,
                "complete",
                JobStatus.RUNNING.value,
                JobStatus.COMPLETED.value,
                "Job completed successfully",
                metadata_json={"job_name": job.name},
            )
            self.conn.commit()
            
        except KeyboardInterrupt as ke:
            logger.info(f"Job {job_id} cancelled by user")
            job.status = JobStatus.CANCELLED.value
            job.error_msg = "Cancelled by user"
            self.repo.save(job)
            write_job_event(self.conn, job_id, "cancel", JobStatus.RUNNING.value, JobStatus.CANCELLED.value, "Job cancelled by user")
            self.conn.commit()
            raise ke
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job.status = JobStatus.FAILED.value
            job.error_msg = str(e)
            self.repo.save(job)
            write_job_event(
                self.conn,
                job_id,
                "fail",
                JobStatus.RUNNING.value,
                JobStatus.FAILED.value,
                f"Job failed: {e}",
                metadata_json={"job_name": job.name, "error": str(e)},
            )
            self.conn.commit()
            raise e

    def _execute_ingest(self, job: Job):
        payload = job.payload_json
        filepath = payload.get("filepath")
        if not filepath:
            raise ValueError("Payload missing 'filepath' key")
        run_ingest(self.conn, self.artifact_store, self.ffmpeg_adapter, filepath, job_id=job.id)

    def _execute_preprocess_all(self, job: Job):
        payload = job.payload_json
        filepath = payload.get("filepath")
        if not filepath:
            raise ValueError("Payload missing 'filepath' key")
            
        rec_holder: Dict[str, Any] = {}

        def ingest_step():
            rec_holder["recording"] = run_ingest(
                self.conn, self.artifact_store, self.ffmpeg_adapter, filepath, job_id=job.id
            )
            return {"recording_id": rec_holder["recording"].id}

        self._run_observed_step(job.id, "ingest", ingest_step)
        rec = rec_holder["recording"]

        self._run_observed_step(
            job.id,
            "diarize",
            lambda: run_diarize(self.conn, self.artifact_store, self.pyannote_adapter, rec.id, job_id=job.id),
        )

        min_dur = payload.get("min_duration", 2.0)
        max_dur = payload.get("max_duration", 10.0)
        self._run_observed_step(
            job.id,
            "slice",
            lambda: run_slice(
                self.conn,
                self.artifact_store,
                self.ffmpeg_adapter,
                rec.id,
                min_duration=min_dur,
                max_duration=max_dur,
                job_id=job.id,
            ),
        )

        self._run_observed_step(
            job.id,
            "clean",
            lambda: run_clean(self.conn, self.artifact_store, self.demucs_adapter, rec.id, job_id=job.id),
        )

        self._run_observed_step(
            job.id,
            "transcribe",
            lambda: run_transcribe(self.conn, self.artifact_store, self.whisper_adapter, rec.id, job_id=job.id),
        )

        min_quality = payload.get("min_quality_score", 0.6)
        self._run_observed_step(
            job.id,
            "score",
            lambda: run_score(self.conn, rec.id, min_quality_score=min_quality),
        )
        self._write_preprocess_failure_summary(job.id, rec.id)

    def _run_observed_step(self, job_id: str, step: str, fn):
        logger.info("Running preprocess step: %s", step)
        write_step_event(self.conn, job_id, step, "started")
        self.conn.commit()
        started = time.monotonic()
        try:
            result = fn()
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            write_step_event(
                self.conn,
                job_id,
                step,
                "failed",
                duration_ms=duration_ms,
                error=str(exc),
            )
            self.conn.commit()
            raise
        duration_ms = int((time.monotonic() - started) * 1000)
        metadata = result if isinstance(result, dict) else {}
        write_step_event(
            self.conn,
            job_id,
            step,
            "succeeded",
            duration_ms=duration_ms,
            metadata_json=metadata,
        )
        self.conn.commit()
        return result

    def _write_preprocess_failure_summary(self, job_id: str, recording_id: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM segments
            WHERE recording_id = ?
              AND status IN ('clean_failed', 'transcribe_failed', 'drop', 'ignored_duration_bounds')
            GROUP BY status;
            """,
            (recording_id,),
        )
        failures = {row["status"]: row["count"] for row in cursor.fetchall()}
        write_job_event(
            self.conn,
            job_id,
            "failure_summary",
            None,
            None,
            "Preprocess segment failure summary",
            metadata_json={
                "recording_id": recording_id,
                "failed_segment_count": sum(failures.values()),
                "failure_counts": failures,
            },
        )
        self.conn.commit()

    def _execute_train_sovits(self, job: Job):
        payload = job.payload_json
        dataset_id = payload.get("dataset_id")
        model_name = payload.get("model_name")
        config = payload.get("config", {})
        model_run_id = payload.get("model_run_id")
        resume_from = payload.get("resume_from_checkpoint_id")
        
        if not dataset_id or not model_name:
            raise ValueError("Payload missing 'dataset_id' or 'model_name'")
            
        run_train_sovits(
            conn=self.conn,
            artifact_store=self.artifact_store,
            sovits_adapter=self.sovits_adapter,
            dataset_id=dataset_id,
            model_name=model_name,
            config=config,
            model_run_id=model_run_id,
            resume_from_checkpoint_id=resume_from,
            job_id=job.id
        )

    # ─────────────────────────────────────────────────────────────────────────
    # V16 fix: per-step execution methods for individual preprocess steps
    # These enable step-level retry without re-running the entire chain.
    # ─────────────────────────────────────────────────────────────────────────

    def _execute_step_diarize(self, job: Job):
        """Dispatch a 'diarize' job for a single recording."""
        from myvoiceclone.pipelines.diarize import run_diarize
        payload = job.payload_json
        recording_id = payload.get("recording_id")
        if not recording_id:
            raise ValueError("Payload missing 'recording_id' key")
        run_diarize(self.conn, self.artifact_store, self.pyannote_adapter, recording_id, job_id=job.id)

    def _execute_step_slice(self, job: Job):
        """Dispatch a 'slice' job for a single recording."""
        from myvoiceclone.pipelines.slice import run_slice
        payload = job.payload_json
        recording_id = payload.get("recording_id")
        if not recording_id:
            raise ValueError("Payload missing 'recording_id' key")
        min_dur = payload.get("min_duration", 2.0)
        max_dur = payload.get("max_duration", 10.0)
        run_slice(self.conn, self.artifact_store, self.ffmpeg_adapter, recording_id,
                  min_duration=min_dur, max_duration=max_dur, job_id=job.id)

    def _execute_step_clean(self, job: Job):
        """Dispatch a 'clean' job for a single recording."""
        from myvoiceclone.pipelines.clean import run_clean
        payload = job.payload_json
        recording_id = payload.get("recording_id")
        if not recording_id:
            raise ValueError("Payload missing 'recording_id' key")
        run_clean(self.conn, self.artifact_store, self.demucs_adapter, recording_id, job_id=job.id)

    def _execute_step_transcribe(self, job: Job):
        """Dispatch a 'transcribe' job for a single recording."""
        from myvoiceclone.pipelines.transcribe import run_transcribe
        payload = job.payload_json
        recording_id = payload.get("recording_id")
        if not recording_id:
            raise ValueError("Payload missing 'recording_id' key")
        run_transcribe(self.conn, self.artifact_store, self.whisper_adapter, recording_id, job_id=job.id)

    def _execute_step_score(self, job: Job):
        """Dispatch a 'score' job for a single recording."""
        from myvoiceclone.pipelines.score import run_score
        payload = job.payload_json
        recording_id = payload.get("recording_id")
        if not recording_id:
            raise ValueError("Payload missing 'recording_id' key")
        min_quality = payload.get("min_quality_score", 0.6)
        run_score(self.conn, recording_id, min_quality_score=min_quality)

    def _execute_step_curate(self, job: Job):
        """Dispatch a 'curate' job for a single recording."""
        from myvoiceclone.pipelines.curate import run_curation
        payload = job.payload_json
        recording_id = payload.get("recording_id")
        if not recording_id:
            raise ValueError("Payload missing 'recording_id' key")
        run_curation(
            self.conn,
            self.artifact_store,
            recording_id,
            min_quality_score=payload.get("min_quality_score", 0.6),
            dedupe=payload.get("dedupe", False),
            job_id=job.id,
        )

    def _execute_infer_real(self, job: Job):
        """Dispatch a first-test real inference job."""
        from myvoiceclone.pipelines.infer_real import RealInferenceRequest, run_real_inference

        payload = job.payload_json
        run_real_inference(
            self.conn,
            self.artifact_store,
            RealInferenceRequest(
                text=payload.get("text", ""),
                reference_artifact_id=payload.get("reference_artifact_id", ""),
                model_id=payload.get("model_id", "tts_models/multilingual/multi-dataset/xtts_v2"),
                source_artifact_id=payload.get("source_artifact_id"),
                language=payload.get("language", "en"),
                adapter_mode=payload.get("adapter_mode", "real"),
                config=payload.get("config", {}),
            ),
            job_id=job.id,
        )

    def _execute_eval_first_test(self, job: Job):
        """Dispatch a first-test artifact evaluation job."""
        from myvoiceclone.pipelines.evaluate import run_first_test_evaluation

        payload = job.payload_json
        run_first_test_evaluation(
            self.conn,
            self.artifact_store,
            run_id=payload.get("run_id") or job.subject_id or job.id,
            inference_artifact_id=payload.get("inference_artifact_id", ""),
            reference_artifact_id=payload.get("reference_artifact_id"),
            metric_source=payload.get("metric_source", "smoke_metric"),
            job_id=job.id,
        )
