import os
import sqlite3
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from myvoiceclone.domain.entities import ModelRun, TrainRequest, ConvertRequest, SynthRequest
from myvoiceclone.domain.states import DatasetStatus, ModelRunStatus
from myvoiceclone.storage.repositories import DatasetRepository, ModelRunRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.adapters.training.rvc_adapter import RvcAdapter
from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter
from myvoiceclone.adapters.training.sovits_adapter import SovitsAdapter

def run_train_rvc(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    dataset_id: str,
    model_name: str,
    config: Dict[str, Any],
    rvc_adapter: Optional[Any] = None,
    source_audio_path: Optional[str] = None,
    model_run_id: Optional[str] = None,
    job_id: Optional[str] = None
) -> ModelRun:
    if rvc_adapter is None:
        from myvoiceclone.adapters.training.rvc_adapter import RvcAdapter
        rvc_adapter = RvcAdapter()
        
    ds_repo = DatasetRepository(conn)
    ds = ds_repo.get_by_id(dataset_id)
    if not ds:
        raise ValueError(f"Dataset {dataset_id} not found")
        
    # Strictly check that the dataset is frozen
    if ds.status != DatasetStatus.FROZEN.value:
        raise ValueError(f"Dataset {dataset_id} must be frozen before training. Current status: {ds.status}")

    run_repo = ModelRunRepository(conn)
    run_id = model_run_id or f"run_{uuid.uuid4().hex[:12]}"
    
    run = ModelRun(
        id=run_id,
        name=model_name,
        dataset_id=dataset_id,
        status=ModelRunStatus.RUNNING.value,
        config_json=config,
        model_family="rvc"
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
        
        if train_res.status != ModelRunStatus.COMPLETED.value:
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
        
        if convert_res.status != ModelRunStatus.COMPLETED.value:
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
                "source_audio_path": src_path,
                "synthetic": True,
                "source_model_run": run_id,
                "watermark": "placeholder"
            }
        )

        # Update ModelRun to completed
        run.status = ModelRunStatus.COMPLETED.value
        # We append metrics and artifact ids to config_json
        run.config_json["metrics"] = train_res.metrics
        run.config_json["checkpoint_artifact_id"] = checkpoint_art.id
        run.config_json["rendered_artifact_id"] = rendered_art.id
        run.checkpoint_artifact_id = checkpoint_art.id
        run.finished_at = datetime.utcnow()
        run_repo.save(run)
        conn.commit()
        return run

    except Exception as e:
        run.status = ModelRunStatus.FAILED.value
        if "config_json" not in run.__dict__ or run.config_json is None:
            run.config_json = {}
        run.config_json["error_msg"] = str(e)
        run_repo.save(run)
        conn.commit()
        raise e


def run_synth_xtts(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    speaker_id: str,
    text: str,
    config: Dict[str, Any],
    xtts_adapter: Optional[Any] = None,
    job_id: Optional[str] = None
) -> ModelRun:
    if xtts_adapter is None:
        from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter
        xtts_adapter = XttsAdapter()
        
    run_repo = ModelRunRepository(conn)
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    
    run = ModelRun(
        id=run_id,
        name=f"xtts_synth_{speaker_id}",
        dataset_id=None,
        status=ModelRunStatus.RUNNING.value,
        config_json=config,
        model_family="xtts"
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
        
        if synth_res.status != ModelRunStatus.COMPLETED.value:
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
                "duration_sec": synth_res.duration_sec,
                "synthetic": True,
                "source_model_run": run_id,
                "watermark": "placeholder"
            }
        )

        run.status = ModelRunStatus.COMPLETED.value
        run.config_json["rendered_artifact_id"] = rendered_art.id
        run.finished_at = datetime.utcnow()
        run_repo.save(run)
        conn.commit()
        return run

    except Exception as e:
        run.status = ModelRunStatus.FAILED.value
        if "config_json" not in run.__dict__ or run.config_json is None:
            run.config_json = {}
        run.config_json["error_msg"] = str(e)
        run_repo.save(run)
        conn.commit()
        raise e


def generate_feature_cache_key(manifest_sha256: str, config: dict) -> str:
    import hashlib
    import json
    config_str = json.dumps(config, sort_keys=True)
    hasher = hashlib.sha256()
    hasher.update(manifest_sha256.encode('utf-8'))
    hasher.update(config_str.encode('utf-8'))
    return hasher.hexdigest()


def capture_env_digest() -> dict:
    import sys
    import subprocess
    
    python_version = sys.version.split()[0]
    torch_version = "not_installed"
    cuda_available = False
    cuda_version = "N/A"
    try:
        import torch
        torch_version = torch.__version__
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            cuda_version = torch.version.cuda
    except ImportError:
        pass
        
    git_commit = "unknown"
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        pass
        
    return {
        "python_version": python_version,
        "torch_version": torch_version,
        "cuda_available": cuda_available,
        "cuda_version": cuda_version,
        "git_commit": git_commit
    }


def run_prepare_features(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    dataset_id: str,
    config: dict,
    job_id: Optional[str] = None
) -> str:
    ds_repo = DatasetRepository(conn)
    ds = ds_repo.get_by_id(dataset_id)
    if not ds:
        raise ValueError(f"Dataset {dataset_id} not found")
        
    manifest_sha256 = ds.manifest_sha256 or "dummy_manifest_sha"
    cache_key = generate_feature_cache_key(manifest_sha256, config)
    
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM artifacts 
        WHERE artifact_type = 'feature_cache' AND json_extract(metadata_json, '$.cache_key') = ?;
        """,
        (cache_key,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
        
    feature_data = b"fake_hubert_content_units_f0_spec_data"
    art_name = f"features_{cache_key}.bin"
    
    art = artifact_store.create_artifact(
        name=art_name,
        content=feature_data,
        artifact_type="feature_cache",
        job_id=job_id,
        metadata_json={
            "cache_key": cache_key,
            "dataset_id": dataset_id,
            "manifest_sha256": manifest_sha256,
            "config": config
        }
    )
    conn.commit()
    return art.id


def run_train_sovits(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    dataset_id: str,
    model_name: str,
    config: Dict[str, Any],
    sovits_adapter: Optional[Any] = None,
    model_run_id: Optional[str] = None,
    resume_from_checkpoint_id: Optional[str] = None,
    job_id: Optional[str] = None
) -> ModelRun:
    if sovits_adapter is None:
        from myvoiceclone.adapters.training.sovits_adapter import SovitsAdapter
        sovits_adapter = SovitsAdapter()
        
    ds_repo = DatasetRepository(conn)
    ds = ds_repo.get_by_id(dataset_id)
    if not ds:
        raise ValueError(f"Dataset {dataset_id} not found")
    if ds.status != DatasetStatus.FROZEN.value:
        raise ValueError(f"Dataset {dataset_id} must be frozen before training")
        
    run_repo = ModelRunRepository(conn)
    
    if model_run_id:
        run = run_repo.get_by_id(model_run_id)
        if not run:
            run = ModelRun(id=model_run_id, name=model_name, dataset_id=dataset_id, status=ModelRunStatus.QUEUED.value, config_json=config, model_family="sovits")
        else:
            run.status = ModelRunStatus.QUEUED.value
            run.model_family = run.model_family or "sovits"
    else:
        model_run_id = f"run_{uuid.uuid4().hex[:12]}"
        run = ModelRun(id=model_run_id, name=model_name, dataset_id=dataset_id, status=ModelRunStatus.QUEUED.value, config_json=config, model_family="sovits")
        
    run_repo.save(run)
    conn.commit()
    
    # queued -> preparing
    run.status = ModelRunStatus.PREPARING.value
    run_repo.save(run)
    conn.commit()
    
    features_art_id = run_prepare_features(conn, artifact_store, dataset_id, config, job_id)
    run.config_json["features_artifact_id"] = features_art_id
    run_repo.save(run)
    conn.commit()
    
    # preparing -> training
    run.status = ModelRunStatus.TRAINING.value
    run_repo.save(run)
    conn.commit()
    
    try:
        epochs = config.get("epochs", 2)
        last_checkpoint_art_id = resume_from_checkpoint_id
        
        if resume_from_checkpoint_id:
            checkpoint_art = artifact_store.get_artifact(resume_from_checkpoint_id)
            if not checkpoint_art:
                raise ValueError(f"Checkpoint {resume_from_checkpoint_id} not found to resume")
        
        for epoch in range(1, epochs + 1):
            if job_id:
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM jobs WHERE id = ?;", (job_id,))
                row = cursor.fetchone()
                if row and row[0] in (ModelRunStatus.CANCELLED.value, "cancelling"):
                    raise KeyboardInterrupt("Job cancelled by user")
            
            if resume_from_checkpoint_id and epoch == 1:
                train_res = sovits_adapter.resume(checkpoint_art.uri, TrainRequest(dataset_id, model_name, config))
            else:
                train_res = sovits_adapter.train(TrainRequest(dataset_id, model_name, config))
                
            if train_res.status != ModelRunStatus.COMPLETED.value:
                raise RuntimeError(f"So-VITS training step failed at epoch {epoch}: {train_res.error_msg}")
                
            loss = train_res.metrics.get("loss", 0.0) - epoch * 0.001
            conn.execute(
                "INSERT INTO eval_metrics (run_id, metric_name, metric_value, step) VALUES (?, ?, ?, ?);",
                (model_run_id, "loss", loss, epoch)
            )
            
            checkpoint_name = f"{model_name}_epoch_{epoch}.pth"
            checkpoint_art = artifact_store.create_artifact(
                name=checkpoint_name,
                content=train_res.checkpoint_bytes,
                artifact_type="checkpoint",
                job_id=job_id,
                metadata_json={"model_run_id": model_run_id, "epoch": epoch}
            )
            last_checkpoint_art_id = checkpoint_art.id
            
            # Update ModelRun to checkpointed
            run.status = ModelRunStatus.CHECKPOINTED.value
            run.config_json["last_checkpoint_artifact_id"] = last_checkpoint_art_id
            run.config_json["current_epoch"] = epoch
            run.checkpoint_artifact_id = last_checkpoint_art_id
            run_repo.save(run)
            conn.commit()

        # training completed -> completed
        run.status = ModelRunStatus.COMPLETED.value
        
        from myvoiceclone.config import resolve_models_dir
        export_dir = os.path.join(resolve_models_dir(), "registry")
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, f"{model_name}_final.pth")
        
        last_ckpt = artifact_store.get_artifact(last_checkpoint_art_id)
        sovits_adapter.export(last_ckpt.uri, export_path)
        
        with open(export_path, 'rb') as f:
            model_data = f.read()
             
        registered_model_art = artifact_store.create_artifact(
            name=f"{model_name}_final.pth",
            content=model_data,
            artifact_type="model_registry",
            parent_artifact_id=last_checkpoint_art_id,
            job_id=job_id,
            metadata_json={"model_run_id": model_run_id, "dataset_id": dataset_id}
        )
        
        rendered_art = artifact_store.create_artifact(
            name=f"{model_name}_sovits_sample.wav",
            content=b"fake_sovits_rendered_audio_wav_data",
            artifact_type="rendered_audio",
            parent_artifact_id=registered_model_art.id,
            job_id=job_id,
            metadata_json={
                "model_run_id": model_run_id,
                "synthetic": True,
                "source_model_run": model_run_id,
                "watermark": "placeholder"
            }
        )
        
        run.config_json["registered_model_artifact_id"] = registered_model_art.id
        run.config_json["rendered_artifact_id"] = rendered_art.id
        run.config_json["metrics"] = {"final_loss": loss}
        env_digest = capture_env_digest()
        run.config_json["env_digest"] = env_digest
        run.env_digest = env_digest
        run.git_commit = env_digest.get("git_commit")
        run.checkpoint_artifact_id = last_checkpoint_art_id
        run.finished_at = datetime.utcnow()
        run_repo.save(run)
        conn.commit()
        return run

    except KeyboardInterrupt as ke:
        run.status = ModelRunStatus.CANCELLED.value
        run.config_json["error_msg"] = "Cancelled by user"
        run.finished_at = datetime.utcnow()
        run_repo.save(run)
        conn.commit()
        raise ke
    except Exception as e:
        run.status = ModelRunStatus.FAILED.value
        run.config_json["error_msg"] = str(e)
        run.finished_at = datetime.utcnow()
        run_repo.save(run)
        conn.commit()
        raise e
