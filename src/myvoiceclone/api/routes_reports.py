import sqlite3
import json
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import ReportResponse, ReleaseGateResponse
from myvoiceclone.domain.states import ReleaseGateStatus
from myvoiceclone.storage.repositories import ReportRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.config import load_local_config
# V5 fix: replaced direct eval imports with domain service layer
from myvoiceclone.services import (
    service_generate_baseline_report,
    service_generate_train_report,
    service_evaluate_long_train_gate,
)
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

class ReleaseGateCreate(BaseModel):
    gate_id: str
    model_run_id: str

class ReleaseGateWaiveRequest(BaseModel):
    approved_by: str
    reason: str

class SubjectiveReportCreate(BaseModel):
    report_id: str
    run_id: str
    abx_score: float
    mos_score: float
    reviewer: str
    comment: str = ""
    sample_artifact_id: Optional[str] = None

def parse_gate_row(row) -> dict:
    d = dict(row)
    if d.get("details_json"):
        try:
            d["details_json"] = json.loads(d["details_json"])
        except Exception:
            d["details_json"] = {}
    else:
        d["details_json"] = {}
    if d.get("decision_json"):
        try:
            d["decision_json"] = json.loads(d["decision_json"])
        except Exception:
            d["decision_json"] = {}
    else:
        d["decision_json"] = {}
    return d


def _json_columns(row, *columns: str) -> dict:
    data = dict(row)
    for column in columns:
        if column in data:
            try:
                data[column] = json.loads(data[column]) if data[column] else {}
            except Exception:
                data[column] = {}
    return data

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
    try:
        # V5 fix: use domain service instead of direct eval call
        return service_generate_baseline_report(db, req.report_id, req.model_run_ids)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reports/train", response_model=ReportResponse)
def create_train_report(req: TrainReportCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        # V5 fix: use domain service instead of direct eval call
        return service_generate_train_report(db, req.report_id, req.model_run_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reports/subjective", response_model=ReportResponse)
def create_subjective_report(req: SubjectiveReportCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        from myvoiceclone.services import service_generate_subjective_report

        return service_generate_subjective_report(
            db,
            report_id=req.report_id,
            run_id=req.run_id,
            abx_score=req.abx_score,
            mos_score=req.mos_score,
            reviewer=req.reviewer,
            comment=req.comment,
            sample_artifact_id=req.sample_artifact_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reports/gate", response_model=Dict[str, Any])
def create_gate_report(req: GateReportCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        # V5 fix: use domain service instead of direct eval call
        return service_evaluate_long_train_gate(db, req.dataset_id, req.baseline_report_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reports/release-gates", response_model=ReleaseGateResponse)
def create_release_gate(req: ReleaseGateCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM model_runs WHERE id = ?;", (req.model_run_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Model run not found")
    
    from myvoiceclone.domain.policies import check_release_policy, evaluate_release_layers
    policy_res = check_release_policy(db, req.model_run_id)
    release_layers = evaluate_release_layers(db, req.model_run_id, policy_res)
    passed = release_layers["smoke_pass"] and release_layers["quality_pass"]
    passed_int = 1 if passed else 0
    gate_status = ReleaseGateStatus.PASSED.value if passed else ReleaseGateStatus.FAILED.value

    details_json = json.dumps(release_layers)
    
    try:
        db.execute(
            """
            INSERT INTO release_gates (id, model_run_id, passed, status, details_json, decision_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (req.gate_id, req.model_run_id, passed_int, gate_status, details_json, details_json)
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
        
    cursor.execute("SELECT * FROM release_gates WHERE id = ?;", (req.gate_id,))
    row = cursor.fetchone()
    return parse_gate_row(row)

@router.post("/reports/release-gates/{gate_id}/waive", response_model=ReleaseGateResponse)
def waive_release_gate(gate_id: str, req: ReleaseGateWaiveRequest, db: sqlite3.Connection = Depends(get_db)):
    if not req.reason.strip():
        raise HTTPException(status_code=400, detail="Waive reason is required")
        
    cursor = db.cursor()
    cursor.execute("SELECT * FROM release_gates WHERE id = ?;", (gate_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Release gate not found")
        
    details = {}
    if row["details_json"]:
        try:
            details = json.loads(row["details_json"])
        except Exception:
            pass
    details["waived"] = True
    details["waived_reason"] = req.reason
    details["manual_waived"] = True
    details.setdefault("blocked_reasons", [])
    
    db.execute(
        """
        UPDATE release_gates 
        SET passed = 1, status = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP, details_json = ?, decision_json = ?
        WHERE id = ?;
        """,
        (ReleaseGateStatus.WAIVED.value, req.approved_by, json.dumps(details), json.dumps(details), gate_id)
    )
    
    db.execute(
        """
        INSERT INTO policy_events (event_type, status, details_json, subject_type, subject_id, policy_name, decision, reason, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "release_gate_waived",
            ReleaseGateStatus.WAIVED.value,
            json.dumps({"gate_id": gate_id, "approved_by": req.approved_by, "reason": req.reason}),
            "release_gate",
            gate_id,
            "release_gate",
            ReleaseGateStatus.WAIVED.value,
            req.reason,
            json.dumps({"approved_by": req.approved_by}),
        )
    )
    db.commit()
    
    cursor.execute("SELECT * FROM release_gates WHERE id = ?;", (gate_id,))
    row = cursor.fetchone()
    return parse_gate_row(row)

@router.get("/reports/release-gates/{gate_id}", response_model=ReleaseGateResponse)
def get_release_gate(gate_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM release_gates WHERE id = ?;", (gate_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Release gate not found")
    return parse_gate_row(row)

@router.get("/audit/trace", response_model=Dict[str, Any])
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
                trace_events.append({"timestamp": get_time(ev, "created_at"), "type": "job_event", "data": _json_columns(ev, "metadata_json")})
                
            # Artifacts produced by this job
            cursor.execute("SELECT * FROM artifacts WHERE job_id = ? OR created_by_job_id = ?;", (subject_id, subject_id))
            arts = cursor.fetchall()
            for art in arts:
                trace_events.append({"timestamp": get_time(art, "created_at"), "type": "artifact", "data": _json_columns(art, "metadata_json", "params_json")})
                
    elif subject_type == "run":
        cursor.execute("SELECT * FROM model_runs WHERE id = ?;", (subject_id,))
        run = cursor.fetchone()
        if run:
            trace_events.append({"timestamp": get_time(run, "created_at"), "type": "model_run", "data": dict(run)})
            
            # Metrics
            cursor.execute("SELECT * FROM eval_metrics WHERE run_id = ?;", (subject_id,))
            metrics = cursor.fetchall()
            for m in metrics:
                trace_events.append({"timestamp": get_time(m, "created_at"), "type": "eval_metric", "data": _json_columns(m, "metric_json")})
                
            # Samples
            cursor.execute("SELECT * FROM eval_samples WHERE run_id = ?;", (subject_id,))
            samples = cursor.fetchall()
            for s in samples:
                trace_events.append({"timestamp": get_time(s, "created_at"), "type": "eval_sample", "data": _json_columns(s, "scores_json")})

            cursor.execute("SELECT * FROM release_gates WHERE model_run_id = ?;", (subject_id,))
            for gate in cursor.fetchall():
                trace_events.append({"timestamp": get_time(gate, "created_at"), "type": "release_gate", "data": _json_columns(gate, "details_json", "decision_json")})

            cursor.execute("SELECT * FROM policy_events WHERE subject_id = ? OR payload_json LIKE ?;", (subject_id, f"%{subject_id}%"))
            for policy in cursor.fetchall():
                trace_events.append({"timestamp": get_time(policy, "created_at"), "type": "policy_event", "data": _json_columns(policy, "details_json", "payload_json")})
                
    elif subject_type == "report":
        cursor.execute("SELECT * FROM reports WHERE id = ?;", (subject_id,))
        rpt = cursor.fetchone()
        if rpt:
            trace_events.append({"timestamp": get_time(rpt, "created_at"), "type": "report", "data": _json_columns(rpt, "summary_json")})

            cursor.execute("SELECT * FROM eval_metrics WHERE report_id = ?;", (subject_id,))
            for metric in cursor.fetchall():
                trace_events.append({"timestamp": get_time(metric, "created_at"), "type": "eval_metric", "data": _json_columns(metric, "metric_json")})

            cursor.execute("SELECT * FROM eval_samples WHERE report_id = ?;", (subject_id,))
            for sample in cursor.fetchall():
                trace_events.append({"timestamp": get_time(sample, "created_at"), "type": "eval_sample", "data": _json_columns(sample, "scores_json")})

            cursor.execute("SELECT * FROM policy_events WHERE subject_type = 'report' AND subject_id = ?;", (subject_id,))
            for policy in cursor.fetchall():
                trace_events.append({"timestamp": get_time(policy, "created_at"), "type": "policy_event", "data": _json_columns(policy, "details_json", "payload_json")})

    elif subject_type == "release_gate":
        cursor.execute("SELECT * FROM release_gates WHERE id = ?;", (subject_id,))
        gate = cursor.fetchone()
        if gate:
            trace_events.append({"timestamp": get_time(gate, "created_at"), "type": "release_gate", "data": _json_columns(gate, "details_json", "decision_json")})
            cursor.execute("SELECT * FROM policy_events WHERE subject_type = 'release_gate' AND subject_id = ?;", (subject_id,))
            for policy in cursor.fetchall():
                trace_events.append({"timestamp": get_time(policy, "created_at"), "type": "policy_event", "data": _json_columns(policy, "details_json", "payload_json")})
            
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
