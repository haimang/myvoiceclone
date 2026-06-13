import json
import sqlite3
from typing import Dict, Any
from myvoiceclone.domain.entities import Report, Artifact
from myvoiceclone.storage.repositories import ReportRepository, DatasetRepository
from myvoiceclone.storage.artifact_store import ArtifactStore

def generate_corpus_report(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    dataset_id: str,
    report_id: str
) -> Report:
    ds_repo = DatasetRepository(conn)
    ds = ds_repo.get_by_id(dataset_id)
    if not ds:
        raise ValueError(f"Dataset {dataset_id} not found")
        
    cursor = conn.cursor()
    
    # 1. Total segments and duration (all statuses)
    cursor.execute("SELECT COUNT(*), SUM(end_sec - start_sec) FROM segments;")
    total_row = cursor.fetchone()
    total_count = total_row[0] or 0
    total_dur = total_row[1] or 0.0
    
    # 2. Dataset segments (frozen in manifest)
    cursor.execute(
        """
        SELECT COUNT(ds.segment_id), SUM(s.end_sec - s.start_sec), AVG(s.quality_score)
        FROM dataset_segments ds
        JOIN segments s ON ds.segment_id = s.id
        WHERE ds.dataset_id = ?;
        """,
        (dataset_id,)
    )
    dataset_row = cursor.fetchone()
    ds_count = dataset_row[0] or 0
    ds_dur = dataset_row[1] or 0.0
    avg_quality = dataset_row[2] or 0.0
    
    # 3. Splits count and duration
    cursor.execute(
        """
        SELECT split, COUNT(*), SUM(s.end_sec - s.start_sec)
        FROM dataset_segments ds
        JOIN segments s ON ds.segment_id = s.id
        WHERE ds.dataset_id = ?
        GROUP BY split;
        """,
        (dataset_id,)
    )
    splits = {}
    for r in cursor.fetchall():
        splits[r[0]] = {"count": r[1], "duration_sec": r[2]}
        
    # 4. Drop reasons
    cursor.execute(
        """
        SELECT reason, COUNT(*) 
        FROM segment_reviews 
        WHERE status_to = 'drop' 
        GROUP BY reason;
        """
    )
    drop_reasons = {r[0]: r[1] for r in cursor.fetchall()}
    
    # 5. Generate summary JSON
    summary = {
        "dataset_id": dataset_id,
        "dataset_name": ds.name,
        "total_segments_scanned": total_count,
        "total_duration_scanned_sec": total_dur,
        "kept_segments_count": ds_count,
        "kept_duration_sec": ds_dur,
        "average_quality_score": avg_quality,
        "splits": splits,
        "drop_reasons": drop_reasons
    }
    
    # 6. Generate Markdown report
    md_content = f"""# Corpus Audit Report for Dataset: {ds.name}

## Summary Metrics
- **Dataset ID**: {dataset_id}
- **Total Audited Segments**: {total_count} ({total_dur:.2f} seconds total)
- **Kept Segments (Frozen)**: {ds_count} ({ds_dur:.2f} seconds total)
- **Average Segment Quality Score**: {avg_quality:.4f}

## Split Distributions
"""
    for split_name, metrics in splits.items():
        md_content += f"- **{split_name.capitalize()}**: {metrics['count']} segments ({metrics['duration_sec']:.2f} seconds)\n"
        
    md_content += "\n## Drop Reasons Audit\n"
    if drop_reasons:
        for reason, count in drop_reasons.items():
            md_content += f"- *{reason}*: {count} segments\n"
    else:
        md_content += "- No segments dropped.\n"
        
    # Save markdown report artifact
    report_bytes = md_content.encode('utf-8')
    report_filename = f"{report_id}_corpus_audit.md"
    report_art = artifact_store.create_artifact(
        name=report_filename,
        content=report_bytes,
        artifact_type="report"
    )
    
    # Save report to DB
    rpt = Report(
        id=report_id,
        name=f"Corpus Audit - {ds.name}",
        report_type="corpus_audit",
        summary_json=summary,
        artifact_id=report_art.id
    )
    
    repo = ReportRepository(conn)
    repo.save(rpt)
    conn.commit()
    
    return rpt
