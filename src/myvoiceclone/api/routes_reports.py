import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import ReportResponse
from myvoiceclone.storage.repositories import ReportRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.config import load_local_config
from myvoiceclone.eval.report import generate_baseline_report, generate_train_report, evaluate_long_train_gate
from pydantic import BaseModel

router = APIRouter(tags=["reports"])

class BaselineReportCreate(BaseModel):
    report_id: str
    model_run_ids: List[str]

class TrainReportCreate(BaseModel):
    report_id: str
    model_run_id: str

class GateReportCreate(BaseModel):
    dataset_id: str
    baseline_report_id: str

@router.get("/reports", response_model=List[ReportResponse])
def list_reports(db: sqlite3.Connection = Depends(get_db)):
    repo = ReportRepository(db)
    return repo.list_all()

@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = ReportRepository(db)
    rpt = repo.get_by_id(report_id)
    if not rpt:
        raise HTTPException(status_code=404, detail="Report not found")
    return rpt

@router.post("/reports/baseline", response_model=ReportResponse)
def create_baseline_report(req: BaselineReportCreate, db: sqlite3.Connection = Depends(get_db)):
    config = load_local_config()
    artifact_store = ArtifactStore(db, config.get("artifact_root", "data/artifacts"))
    try:
        return generate_baseline_report(db, artifact_store, req.report_id, req.model_run_ids)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reports/train", response_model=ReportResponse)
def create_train_report(req: TrainReportCreate, db: sqlite3.Connection = Depends(get_db)):
    config = load_local_config()
    artifact_store = ArtifactStore(db, config.get("artifact_root", "data/artifacts"))
    try:
        return generate_train_report(db, artifact_store, req.report_id, req.model_run_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reports/gate")
def create_gate_report(req: GateReportCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        return evaluate_long_train_gate(db, req.dataset_id, req.baseline_report_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/audit/trace")
def get_audit_trace(subject_id: str, subject_type: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    trace_events = []
    
    # helper to parse date standard
    def get_time(row_dict, key):
        return dict(row_dict).get(key) or "1970-01-01 00:00:00"
        
    if subject_type == "recording":
        # Get recording info
        cursor.execute("SELECT * FROM recordings WHERE id = ?;", (subject_id,))
        rec = cursor.fetchone()
        if rec:
            trace_events.append({"timestamp": get_time(rec, "created_at"), "type": "recording", "data": dict(rec)})
            
            # Get segments
            cursor.execute("SELECT * FROM segments WHERE recording_id = ?;", (subject_id,))
            segs = cursor.fetchall()
            for seg in segs:
                trace_events.append({"timestamp": get_time(seg, "created_at"), "type": "segment", "data": dict(seg)})
                
                # Segment reviews
                cursor.execute("SELECT * FROM segment_reviews WHERE segment_id = ?;", (seg["id"],))
                revs = cursor.fetchall()
                for rev in revs:
                    trace_events.append({"timestamp": get_time(rev, "created_at"), "type": "segment_review", "data": dict(rev)})
                    
    elif subject_type == "dataset":
        cursor.execute("SELECT * FROM datasets WHERE id = ?;", (subject_id,))
        ds = cursor.fetchone()
        if ds:
            trace_events.append({"timestamp": get_time(ds, "created_at"), "type": "dataset", "data": dict(ds)})
            
            # Model runs trained on this dataset
            cursor.execute("SELECT * FROM model_runs WHERE dataset_id = ?;", (subject_id,))
            runs = cursor.fetchall()
            for run in runs:
                trace_events.append({"timestamp": get_time(run, "created_at"), "type": "model_run", "data": dict(run)})
                
    elif subject_type == "job":
        cursor.execute("SELECT * FROM jobs WHERE id = ?;", (subject_id,))
        job = cursor.fetchone()
        if job:
            trace_events.append({"timestamp": get_time(job, "created_at"), "type": "job", "data": dict(job)})
            
            # Job events
            cursor.execute("SELECT * FROM job_events WHERE job_id = ?;", (subject_id,))
            evs = cursor.fetchall()
            for ev in evs:
                trace_events.append({"timestamp": get_time(ev, "created_at"), "type": "job_event", "data": dict(ev)})
                
            # Artifacts produced by this job
            cursor.execute("SELECT * FROM artifacts WHERE job_id = ?;", (subject_id,))
            arts = cursor.fetchall()
            for art in arts:
                trace_events.append({"timestamp": get_time(art, "created_at"), "type": "artifact", "data": dict(art)})
                
    elif subject_type == "run":
        cursor.execute("SELECT * FROM model_runs WHERE id = ?;", (subject_id,))
        run = cursor.fetchone()
        if run:
            trace_events.append({"timestamp": get_time(run, "created_at"), "type": "model_run", "data": dict(run)})
            
            # Metrics
            cursor.execute("SELECT * FROM eval_metrics WHERE run_id = ?;", (subject_id,))
            metrics = cursor.fetchall()
            for m in metrics:
                trace_events.append({"timestamp": get_time(m, "created_at"), "type": "eval_metric", "data": dict(m)})
                
            # Samples
            cursor.execute("SELECT * FROM eval_samples WHERE run_id = ?;", (subject_id,))
            samples = cursor.fetchall()
            for s in samples:
                trace_events.append({"timestamp": get_time(s, "created_at"), "type": "eval_sample", "data": dict(s)})
                
    elif subject_type == "report":
        cursor.execute("SELECT * FROM reports WHERE id = ?;", (subject_id,))
        rpt = cursor.fetchone()
        if rpt:
            trace_events.append({"timestamp": get_time(rpt, "created_at"), "type": "report", "data": dict(rpt)})
            
    else:
        raise HTTPException(status_code=400, detail="Invalid subject_type")
        
    if not trace_events:
        raise HTTPException(status_code=404, detail="No trace data found for the subject")
        
    # Sort events by timestamp
    trace_events.sort(key=lambda x: x["timestamp"])
    return {
        "subject_id": subject_id,
        "subject_type": subject_type,
        "trace_events": trace_events
    }
