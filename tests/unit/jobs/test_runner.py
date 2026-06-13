import pytest
from myvoiceclone.jobs.queue import JobQueue
from myvoiceclone.jobs.runner import JobRunner
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter
from myvoiceclone.storage.repositories import JobRepository, SegmentRepository

@pytest.mark.unit
def test_job_runner_success_preprocess(db_conn, artifact_store, synthetic_wav):
    queue = JobQueue(db_conn)
    job = queue.enqueue("preprocess_all", {"filepath": synthetic_wav})
    
    assert job.status == "pending"
    
    runner = JobRunner(
        conn=db_conn,
        artifact_store=artifact_store,
        ffmpeg_adapter=FFmpegAdapter(),
        pyannote_adapter=PyannoteAdapter(),
        demucs_adapter=DemucsAdapter(),
        whisper_adapter=WhisperAdapter()
    )
    
    runner.run(job.id)
    
    job_repo = JobRepository(db_conn)
    job_after = job_repo.get_by_id(job.id)
    assert job_after.status == "completed"
    assert job_after.error_msg is None
    
    # Check that events were written
    events = job_repo.get_events(job.id)
    assert len(events) >= 3  # enqueue, start, complete
    assert events[1].status_to == "running"
    assert events[-1].status_to == "completed"
    step_events = [e for e in events if e.event_type.startswith("step_")]
    assert {e.metadata_json["step"] for e in step_events if e.event_type == "step_succeeded"} == {
        "ingest",
        "diarize",
        "slice",
        "clean",
        "transcribe",
        "score",
    }
    assert all("duration_ms" in e.metadata_json for e in step_events if e.event_type == "step_succeeded")
    summaries = [e for e in events if e.event_type == "failure_summary"]
    assert summaries
    assert summaries[0].metadata_json["failed_segment_count"] == 0
    
    # Check that segments were created and scored
    seg_repo = SegmentRepository(db_conn)
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, status FROM recordings;")
    rec_row = cursor.fetchone()
    rec_id = rec_row["id"]
    assert rec_row["status"] == "scored"
    segments = seg_repo.list_by_recording(rec_id)
    assert len(segments) == 2
    assert all(s.status == "processed" for s in segments)

@pytest.mark.unit
def test_job_runner_failure(db_conn, artifact_store):
    queue = JobQueue(db_conn)
    # File does not exist, should fail
    job = queue.enqueue("preprocess_all", {"filepath": "/tmp/nonexistent.wav"})
    
    runner = JobRunner(
        conn=db_conn,
        artifact_store=artifact_store,
        ffmpeg_adapter=FFmpegAdapter(),
        pyannote_adapter=PyannoteAdapter(),
        demucs_adapter=DemucsAdapter(),
        whisper_adapter=WhisperAdapter()
    )
    
    with pytest.raises(Exception):
        runner.run(job.id)
        
    job_repo = JobRepository(db_conn)
    job_after = job_repo.get_by_id(job.id)
    assert job_after.status == "failed"
    assert "Source file not found" in job_after.error_msg
    
    events = job_repo.get_events(job.id)
    assert events[-1].status_to == "failed"
    failed_steps = [e for e in events if e.event_type == "step_failed"]
    assert failed_steps
    assert failed_steps[0].metadata_json["step"] == "ingest"
    assert "Source file not found" in failed_steps[0].metadata_json["error"]
    assert "traceback" in failed_steps[0].metadata_json
    assert "traceback" in events[-1].metadata_json


@pytest.mark.unit
def test_job_runner_curate_step_marks_processed_segments_keep(db_conn, artifact_store):
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_curate', 'uri', 'sha', 3.0, 16000, 1, 'processed');
        """
    )
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, quality_score)
        VALUES ('seg_curate', 'rec_curate', 0.0, 3.0, 'processed', 0.9);
        """
    )
    db_conn.commit()
    queue = JobQueue(db_conn)
    job = queue.enqueue("curate", {"recording_id": "rec_curate"})

    JobRunner(db_conn, artifact_store).run(job.id)

    row = db_conn.execute("SELECT status, metadata_json FROM segments WHERE id = 'seg_curate';").fetchone()
    assert row["status"] == "keep"
    events = JobRepository(db_conn).get_events(job.id)
    assert events[-1].status_to == "completed"
    assert any(e.event_type == "step_succeeded" and e.metadata_json["step"] == "curate" for e in events)


@pytest.mark.unit
def test_job_runner_dispatches_infer_real(db_conn, artifact_store, monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "true")
    reference = artifact_store.create_artifact(
        name="reference.wav",
        content=b"RIFFreference",
        artifact_type="cleaned",
        metadata_json={"adapter_mode": "real"},
    )
    queue = JobQueue(db_conn)
    job = queue.enqueue(
        "infer_real",
        {"text": "hello", "reference_artifact_id": reference.id, "adapter_mode": "mock"},
    )

    JobRunner(db_conn, artifact_store).run(job.id)

    row = db_conn.execute("SELECT id, artifact_type, job_id FROM artifacts WHERE job_id = ?;", (job.id,)).fetchone()
    assert row is not None
    assert row["artifact_type"] == "rendered_audio"
    assert row["job_id"] == job.id
    events = JobRepository(db_conn).get_events(job.id)
    assert any(e.event_type == "step_succeeded" and e.metadata_json["step"] == "infer_real" for e in events)


@pytest.mark.unit
def test_job_runner_dispatches_eval_first_test(db_conn, artifact_store, synthetic_wav):
    with open(synthetic_wav, "rb") as handle:
        wav_bytes = handle.read()
    inference_artifact = artifact_store.create_artifact(
        name="rendered.wav",
        content=wav_bytes,
        artifact_type="rendered_audio",
        metadata_json={"adapter_mode": "real"},
    )
    queue = JobQueue(db_conn)
    job = queue.enqueue(
        "eval_first_test",
        {"run_id": "run_eval", "inference_artifact_id": inference_artifact.id},
    )

    JobRunner(db_conn, artifact_store).run(job.id)

    report = db_conn.execute("SELECT * FROM reports WHERE subject_id = 'run_eval';").fetchone()
    assert report is not None
    assert report["report_type"] == "first_test_eval"
    events = JobRepository(db_conn).get_events(job.id)
    assert events[-1].status_to == "completed"
    assert any(e.event_type == "step_succeeded" and e.metadata_json["step"] == "eval_first_test" for e in events)
