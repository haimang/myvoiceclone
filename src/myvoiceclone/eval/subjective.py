import sqlite3
import os
import json
from typing import Dict, Any
from myvoiceclone.domain.entities import Report
from myvoiceclone.storage.repositories import ReportRepository, ModelRunRepository
from myvoiceclone.storage.artifact_store import ArtifactStore

def generate_subjective_report(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    report_id: str,
    run_id: str,
    abx_score: float,  # e.g. 0.88 preference rate
    mos_score: float,  # e.g. 4.2 out of 5.0
    reviewer: str = "local-reviewer",
    comment: str = "",
    sample_artifact_id: str = None,
) -> Report:
    report_repo = ReportRepository(conn)
    run_repo = ModelRunRepository(conn)
    
    run = run_repo.get_by_id(run_id)
    if not run:
        raise ValueError(f"Model run {run_id} not found")
    if not 1.0 <= mos_score <= 5.0:
        raise ValueError("MOS score must be between 1.0 and 5.0")
    if not 0.0 <= abx_score <= 1.0:
        raise ValueError("ABX score must be between 0.0 and 1.0")
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer is required")
        
    initial_summary = {
        "status": "draft",
        "model_run_id": run_id,
        "metric_source": "manual_mos",
        "abx_score": abx_score,
        "mos_score": mos_score,
        "reviewer": reviewer,
        "comment": comment,
    }
    
    draft_report = Report(
        id=report_id,
        name=f"Subjective Evaluation - {run.name}",
        report_type="subjective_report",
        summary_json=initial_summary,
        artifact_id=None
    )
    report_repo.save(draft_report)
    conn.commit()
    
    # Render subjective evaluation Markdown
    md_content = f"# Subjective Listening Evaluation Report: {report_id}\n\n"
    md_content += f"- **Target Model Run**: {run.name} ({run_id})\n"
    md_content += f"- **MOS (Mean Opinion Score)**: {mos_score:.2f} / 5.0\n"
    md_content += f"- **ABX Preference Rate**: {abx_score * 100:.1f}%\n\n"
    md_content += "## Sample Bundle Details\n"
    
    rendered_art_id = sample_artifact_id or run.config_json.get("rendered_artifact_id")
    if rendered_art_id:
        art = artifact_store.get_artifact(rendered_art_id)
        if art:
            md_content += f"- **Rendered Sample Link**: [{art.uri}](file://{os.path.join(artifact_store.root_dir, art.uri)})\n"
    else:
        md_content += "- *Warning: No rendered voice sample was linked to this model run.*\n"
        
    md_content += "\n## Panel Notes\n"
    md_content += "- Double-blind listening test conducted locally.\n"
    md_content += "- MOS scoring criteria: 1=Bad, 2=Poor, 3=Fair, 4=Good, 5=Excellent.\n"
    
    report_bytes = md_content.encode('utf-8')
    report_filename = f"{report_id}_subjective_report.md"
    report_art = artifact_store.create_artifact(
        name=report_filename,
        content=report_bytes,
        artifact_type="report"
    )
    
    # Update to generated
    final_summary = {
        "status": "generated",
        "model_run_id": run_id,
        "metric_source": "manual_mos",
        "adapter_mode": run.config_json.get("adapter_mode", "unknown"),
        "abx_score": abx_score,
        "mos_score": mos_score,
        "reviewer": reviewer,
        "comment": comment,
        "rendered_artifact_id": rendered_art_id
    }
    if rendered_art_id:
        sample_id = f"manual_{report_id}"
        conn.execute(
            """
            INSERT OR REPLACE INTO eval_samples (
                id, run_id, report_id, prompt, audio_artifact_id, output_artifact_id, scores_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                sample_id,
                run_id,
                report_id,
                "manual MOS/ABX local review",
                rendered_art_id,
                rendered_art_id,
                json.dumps(final_summary),
            ),
        )
    draft_report.summary_json = final_summary
    draft_report.artifact_id = report_art.id
    draft_report.subject_type = "run"
    draft_report.subject_id = run_id
    draft_report.status = "completed"
    report_repo.save(draft_report)
    conn.commit()
    
    return draft_report
