import os
import sqlite3
import uuid
from typing import Dict, Any, Optional
from myvoiceclone.domain.entities import ModelRun, TrainRequest, ConvertRequest, SynthRequest
from myvoiceclone.storage.repositories import DatasetRepository, ModelRunRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.adapters.training.rvc_adapter import RvcAdapter
from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter

def run_train_rvc(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    rvc_adapter: RvcAdapter,
    dataset_id: str,
    model_name: str,
    config: Dict[str, Any],
    source_audio_path: Optional[str] = None,
    job_id: Optional[str] = None
) -> ModelRun:
    ds_repo = DatasetRepository(conn)
    ds = ds_repo.get_by_id(dataset_id)
    if not ds:
        raise ValueError(f"Dataset {dataset_id} not found")
        
    # Strictly check that the dataset is frozen
    if ds.status != "frozen":
        raise ValueError(f"Dataset {dataset_id} must be frozen before training. Current status: {ds.status}")

    run_repo = ModelRunRepository(conn)
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    
    run = ModelRun(
        id=run_id,
        name=model_name,
        dataset_id=dataset_id,
        status="running",
        config_json=config
    )
    run_repo.save(run)
    conn.commit()

    try:
        # 1. Train
        train_req = TrainRequest(
            dataset_id=dataset_id,
            model_name=model_name,
            config=config
        )
        train_res = rvc_adapter.train(train_req)
        
        if train_res.status != "completed":
            raise RuntimeError(f"RVC training failed: {train_res.error_msg}")

        # Save checkpoint artifact
        checkpoint_name = f"{model_name}_checkpoint.pth"
        checkpoint_art = artifact_store.create_artifact(
            name=checkpoint_name,
            content=train_res.checkpoint_bytes,
            artifact_type="checkpoint",
            job_id=job_id,
            metadata_json={"model_run_id": run_id}
        )

        # 2. Convert sample (Voice Conversion)
        # Use dummy source path if not provided
        src_path = source_audio_path or "fake_source_audio.wav"
        convert_req = ConvertRequest(
            model_run_id=run_id,
            source_audio_path=src_path,
            config=config
        )
        convert_res = rvc_adapter.convert(convert_req)
        
        if convert_res.status != "completed":
            raise RuntimeError(f"RVC audio conversion failed: {convert_res.error_msg}")

        # Save rendered sample artifact
        sample_name = f"{model_name}_rendered_sample.wav"
        rendered_art = artifact_store.create_artifact(
            name=sample_name,
            content=convert_res.audio_bytes,
            artifact_type="rendered_audio",
            parent_artifact_id=checkpoint_art.id,
            job_id=job_id,
            metadata_json={
                "model_run_id": run_id,
                "duration_sec": convert_res.duration_sec,
                "source_audio_path": src_path
            }
        )

        # Update ModelRun to completed
        run.status = "completed"
        # We append metrics and artifact ids to config_json
        run.config_json["metrics"] = train_res.metrics
        run.config_json["checkpoint_artifact_id"] = checkpoint_art.id
        run.config_json["rendered_artifact_id"] = rendered_art.id
        run_repo.save(run)
        conn.commit()
        return run

    except Exception as e:
        run.status = "failed"
        if "config_json" not in run.__dict__ or run.config_json is None:
            run.config_json = {}
        run.config_json["error_msg"] = str(e)
        run_repo.save(run)
        conn.commit()
        raise e


def run_synth_xtts(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    xtts_adapter: XttsAdapter,
    speaker_id: str,
    text: str,
    config: Dict[str, Any],
    job_id: Optional[str] = None
) -> ModelRun:
    run_repo = ModelRunRepository(conn)
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    
    run = ModelRun(
        id=run_id,
        name=f"xtts_synth_{speaker_id}",
        dataset_id=None,
        status="running",
        config_json=config
    )
    run_repo.save(run)
    conn.commit()

    try:
        # Synthesize audio
        synth_req = SynthRequest(
            text=text,
            speaker_id=speaker_id,
            config=config
        )
        synth_res = xtts_adapter.synth(synth_req)
        
        if synth_res.status != "completed":
            raise RuntimeError(f"XTTS synthesis failed: {synth_res.error_msg}")

        # Save synthetic audio artifact
        sample_name = f"tts_{speaker_id}_synth.wav"
        rendered_art = artifact_store.create_artifact(
            name=sample_name,
            content=synth_res.audio_bytes,
            artifact_type="rendered_audio",
            job_id=job_id,
            metadata_json={
                "model_run_id": run_id,
                "text": text,
                "speaker_id": speaker_id,
                "duration_sec": synth_res.duration_sec
            }
        )

        run.status = "completed"
        run.config_json["rendered_artifact_id"] = rendered_art.id
        run_repo.save(run)
        conn.commit()
        return run

    except Exception as e:
        run.status = "failed"
        if "config_json" not in run.__dict__ or run.config_json is None:
            run.config_json = {}
        run.config_json["error_msg"] = str(e)
        run_repo.save(run)
        conn.commit()
        raise e
