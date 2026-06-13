import sqlite3
import os
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
    mos_score: float   # e.g. 4.2 out of 5.0
) -> Report:
    report_repo = ReportRepository(conn)
    run_repo = ModelRunRepository(conn)
    
    run = run_repo.get_by_id(run_id)
    if not run:
        raise ValueError(f"Model run {run_id} not found")
        
    initial_summary = {
        "status": "draft",
        "model_run_id": run_id,
        "abx_score": abx_score,
        "mos_score": mos_score
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
    
    rendered_art_id = run.config_json.get("rendered_artifact_id")
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
        "abx_score": abx_score,
        "mos_score": mos_score,
        "rendered_artifact_id": rendered_art_id
    }
    draft_report.summary_json = final_summary
    draft_report.artifact_id = report_art.id
    report_repo.save(draft_report)
    conn.commit()
    
    return draft_report
