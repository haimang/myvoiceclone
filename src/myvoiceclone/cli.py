import os
import sqlite3
import uuid
import typer
from typing import Optional, List
from myvoiceclone.config import resolve_artifact_root, resolve_db_path
from myvoiceclone.storage.sqlite import get_connection
from myvoiceclone.storage.migrations import run_migrations
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.storage.repositories import JobRepository, DatasetRepository, SegmentRepository, ReportRepository, ModelRunRepository
from myvoiceclone.domain.entities import Job, Dataset, ModelRun
from myvoiceclone.domain.states import DatasetStatus, JobStatus, SegmentStatus
from myvoiceclone.jobs.runner import JobRunner

# No adapter imports here to comply with architecture rules

app = typer.Typer(help="MyVoiceClone CLI command line interface")

run_app = typer.Typer(help="Run pipeline steps")
app.add_typer(run_app, name="run")

curate_app = typer.Typer(help="Curate dataset segments")
app.add_typer(curate_app, name="curate")

dataset_app = typer.Typer(help="Manage datasets")
app.add_typer(dataset_app, name="dataset")

train_app = typer.Typer(help="Train voice clone models")
app.add_typer(train_app, name="train")

infer_app = typer.Typer(help="Perform model inference")
app.add_typer(infer_app, name="infer")

report_app = typer.Typer(help="Show or audit reports")
app.add_typer(report_app, name="report")

def get_db_conn():
    return get_connection(resolve_db_path(), load_vec=True)

@app.command("init-db")
def init_db(db: Optional[str] = typer.Option(None, help="Database path")):
    db_path = resolve_db_path(db)
        
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "db", "migrations")
    
    typer.echo(f"Initializing database at: {db_path}")
    run_migrations(db_path, migrations_dir)
    typer.echo("Database initialized successfully.")

@app.command("vec-health")
def vec_health():
    conn = None
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT vec_version();")
        ver = cursor.fetchone()[0]
        typer.echo(f"sqlite-vec loaded successfully. Version: {ver}")
    except Exception as e:
        typer.echo(f"Error checking sqlite-vec: {e}")
        raise typer.Exit(code=1)
    finally:
        if conn:
            conn.close()

@app.command("ingest")
def ingest(filepath: str, dry_run: bool = typer.Option(False, "--dry-run", help="Dry run execute")):
    if dry_run:
        typer.echo(f"[Dry-run] Would ingest recording from path: {filepath}")
        return
        
    conn = get_db_conn()
    try:
        job_repo = JobRepository(conn)
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = Job(id=job_id, name="ingest", status=JobStatus.PENDING.value, payload_json={"filepath": filepath})
        job_repo.save(job)
        conn.commit()
        
        typer.echo(f"Created ingest job: {job_id}")
        
        # Run it synchronously
        artifact_store = ArtifactStore(conn, resolve_artifact_root())
        runner = JobRunner(conn, artifact_store)
        runner.run(job_id)
        
        typer.echo(f"Ingested successfully. Job status: completed.")
    finally:
        conn.close()

@run_app.command("preprocess-all")
def run_preprocess_all(
    filepath: str = typer.Argument(..., help="Audio file path to ingest and preprocess"),
    min_duration: float = typer.Option(2.0, help="Minimum segment duration in seconds"),
    max_duration: float = typer.Option(10.0, help="Maximum segment duration in seconds"),
    min_quality_score: float = typer.Option(0.6, help="Minimum segment quality threshold"),
):
    _run_step_job(
        "preprocess_all",
        {
            "filepath": filepath,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "min_quality_score": min_quality_score,
        },
    )


@run_app.command("diarize")
def run_diarize(recording_id: str):
    _run_step_job("diarize", {"recording_id": recording_id})

def _run_step_job(name: str, payload: dict):
    conn = get_db_conn()
    try:
        job_repo = JobRepository(conn)
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = Job(id=job_id, name=name, status=JobStatus.PENDING.value, payload_json=payload)
        job_repo.save(job)
        conn.commit()
        
        typer.echo(f"Created job {name}: {job_id}")
        
        artifact_store = ArtifactStore(conn, resolve_artifact_root())
        runner = JobRunner(conn, artifact_store)
        runner.run(job_id)
        typer.echo(f"Job {job_id} completed successfully.")
    finally:
        conn.close()

@curate_app.command("list")
def curate_list(status: str = typer.Option(SegmentStatus.NEEDS_REVIEW.value, help="Filter segments by status")):
    conn = get_db_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, recording_id, start_sec, end_sec, status FROM segments WHERE status = ?;", (status,))
        rows = cursor.fetchall()
        typer.echo(f"Segments with status '{status}':")
        for r in rows:
            typer.echo(f" - ID: {r['id']} | Rec: {r['recording_id']} | Time: {r['start_sec']}s-{r['end_sec']}s")
    finally:
        conn.close()

@curate_app.command("mark")
def curate_mark(segment_id: str, status: str = typer.Option(..., help="New status to set"), reason: Optional[str] = typer.Option(None, help="Review reason"), reviewer: str = typer.Option("CLI", help="Reviewer name")):
    conn = get_db_conn()
    try:
        seg_repo = SegmentRepository(conn)
        seg = seg_repo.get_by_id(segment_id)
        if not seg:
            typer.echo(f"Segment {segment_id} not found")
            raise typer.Exit(code=1)
            
        old_status = seg.status
        seg.status = status
        seg_repo.save(seg)
        
        review_id = f"rev_{uuid.uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO segment_reviews (id, segment_id, status_from, status_to, reason, reviewer)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (review_id, segment_id, old_status, status, reason, reviewer)
        )
        conn.commit()
        typer.echo(f"Marked segment {segment_id} as '{status}' successfully.")
    finally:
        conn.close()

@dataset_app.command("create")
def dataset_create(name: str, filter_status: str = typer.Option(SegmentStatus.KEEP.value, help="Status filter for segments")):
    conn = get_db_conn()
    try:
        repo = DatasetRepository(conn)
        ds_id = f"ds_{uuid.uuid4().hex[:12]}"
        ds = Dataset(id=ds_id, name=name, status=DatasetStatus.ACTIVE.value, filter_json={"status": filter_status})
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM segments WHERE status = ? AND cleaned_artifact_id IS NOT NULL;", (filter_status,))
        segments = cursor.fetchall()
        
        repo.save(ds)
        for seg in segments:
            repo.add_segment(ds_id, seg["id"], "train")
            
        conn.commit()
        typer.echo(f"Created active dataset '{name}' (ID: {ds_id}) with {len(segments)} segments.")
    finally:
        conn.close()

@dataset_app.command("freeze")
def dataset_freeze(name: str):
    conn = get_db_conn()
    try:
        # Find dataset by name
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM datasets WHERE name = ? ORDER BY created_at DESC LIMIT 1;", (name,))
        row = cursor.fetchone()
        if not row:
            typer.echo(f"Dataset '{name}' not found")
            raise typer.Exit(code=1)
            
        dataset_id = row["id"]
        from myvoiceclone.services import service_export_dataset

        frozen_ds = service_export_dataset(conn=conn, dataset_id=dataset_id, name=name)
        typer.echo(f"Dataset '{name}' frozen successfully. Manifest checksum: {frozen_ds.manifest_sha256}")
    finally:
        conn.close()

@train_app.command("rvc")
def train_rvc(dataset: str, profile: str = "quick"):
    typer.echo(f"Training RVC model on dataset '{dataset}' with profile '{profile}'...")
    # Run simple train pipeline
    conn = get_db_conn()
    try:
        # Find dataset_id
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM datasets WHERE name = ? ORDER BY created_at DESC LIMIT 1;", (dataset,))
        row = cursor.fetchone()
        if not row:
             typer.echo(f"Dataset '{dataset}' not found")
             raise typer.Exit(code=1)
             
        dataset_id = row["id"]
        
        # V6 fix: use domain service instead of direct pipeline import
        from myvoiceclone.services import service_train_rvc
        
        run = service_train_rvc(
             conn=conn,
             dataset_id=dataset_id,
             model_name=f"rvc_{dataset}_{profile}",
             config={"profile": profile}
        )
        typer.echo(f"RVC Training completed successfully. Model Run ID: {run.id}")
    finally:
        conn.close()

@train_app.command("sovits")
def train_sovits(dataset: str, profile: str = "long"):
    typer.echo(f"Training So-VITS model on dataset '{dataset}' with profile '{profile}'...")
    conn = get_db_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM datasets WHERE name = ? ORDER BY created_at DESC LIMIT 1;", (dataset,))
        row = cursor.fetchone()
        if not row:
             typer.echo(f"Dataset '{dataset}' not found")
             raise typer.Exit(code=1)
             
        dataset_id = row["id"]
        
        # V6 fix: use domain service instead of direct pipeline import
        from myvoiceclone.services import service_train_sovits
        
        run = service_train_sovits(
             conn=conn,
             dataset_id=dataset_id,
             model_name=f"sovits_{dataset}_{profile}",
             config={"profile": profile, "epochs": 2}
        )
        typer.echo(f"So-VITS Training completed successfully. Model Run ID: {run.id}")
    finally:
        conn.close()

@app.command("eval")
def evaluate(run_id: str, suite: str = typer.Option("default", help="Evaluation suite name")):
    typer.echo(f"Running evaluation on model run '{run_id}' with suite '{suite}'...")
    conn = get_db_conn()
    try:
        # Check model run
        run_repo = ModelRunRepository(conn)
        run = run_repo.get_by_id(run_id)
        if not run:
            typer.echo(f"Model run {run_id} not found")
            raise typer.Exit(code=1)
            
        from myvoiceclone.services import service_run_evaluation

        result = service_run_evaluation(conn, run_id)
        typer.echo(f"Evaluation completed with status: {result.get('status', 'unknown')}")
    finally:
        conn.close()

@infer_app.command("vc")
def infer_vc(model: str, input_path: str, out_path: str):
    typer.echo(f"Performing Voice Conversion inference using model '{model}'...")
    if not os.path.exists(input_path):
        typer.echo(f"Input file {input_path} not found")
        raise typer.Exit(code=1)
        
    # Mock inference
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(b"fake_rendered_converted_voice_output")
    typer.echo(f"Inference complete. Output saved to {out_path}")


@infer_app.command("real")
def infer_real(
    text: str = typer.Option(..., help="Text to synthesize"),
    reference_artifact_id: str = typer.Option(..., help="Reference cleaned audio artifact id"),
    model_id: str = typer.Option("tts_models/multilingual/multi-dataset/xtts_v2", help="Inference model id"),
    language: str = typer.Option("en", help="Synthesis language"),
):
    conn = get_db_conn()
    try:
        from myvoiceclone.services import service_run_real_inference

        artifact = service_run_real_inference(
            conn=conn,
            text=text,
            reference_artifact_id=reference_artifact_id,
            model_id=model_id,
            language=language,
            adapter_mode="real",
        )
        typer.echo(f"Inference artifact: {artifact.id}")
        typer.echo(f"URI: {artifact.uri}")
    except Exception as e:
        typer.echo(f"Real inference failed: {e}")
        raise typer.Exit(code=1)
    finally:
        conn.close()

@report_app.command("show")
def report_show(report_id: str):
    conn = get_db_conn()
    try:
        repo = ReportRepository(conn)
        rpt = repo.get_by_id(report_id)
        if not rpt:
            typer.echo(f"Report {report_id} not found")
            raise typer.Exit(code=1)
            
        typer.echo(f"=== Report: {rpt.name} ===")
        typer.echo(f"Type: {rpt.report_type}")
        import json
        typer.echo(f"Summary: {json.dumps(rpt.summary_json, indent=2)}")
    finally:
        conn.close()

@app.command("audit")
def audit(recording_id: str):
    conn = get_db_conn()
    try:
        # Check recording
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recordings WHERE id = ?;", (recording_id,))
        rec = cursor.fetchone()
        if not rec:
            typer.echo(f"Recording {recording_id} not found")
            raise typer.Exit(code=1)
            
        typer.echo(f"=== Audit Log for Recording: {recording_id} ===")
        typer.echo(f"URI: {rec['source_uri']}")
        typer.echo(f"Status: {rec['status']}")
        
        # Get segments
        cursor.execute("SELECT id, status FROM segments WHERE recording_id = ?;", (recording_id,))
        segs = cursor.fetchall()
        typer.echo(f"Segments count: {len(segs)}")
        for s in segs:
            typer.echo(f" - Segment ID: {s['id']} | Status: {s['status']}")
    finally:
        conn.close()


def main():
    app()

if __name__ == "__main__":
    main()
