import os
import pytest
from myvoiceclone.domain.entities import ModelRun
from myvoiceclone.storage.repositories import ModelRunRepository, ReportRepository
from myvoiceclone.eval.subjective import generate_subjective_report

@pytest.mark.unit
def test_generate_subjective_report_success(db_conn, artifact_store):
    run_repo = ModelRunRepository(db_conn)
    # Setup model run
    run_id = "run_sub_1"
    run_repo.save(ModelRun(
        id=run_id,
        name="sovits_subjective",
        dataset_id=None,
        status="completed",
        config_json={"rendered_artifact_id": "art_sub_sample"}
    ))
    # Save mock artifact
    db_conn.execute(
        """
        INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type)
        VALUES ('art_sub_sample', 'sample.wav', 'rendered_audio/sample.wav', 'sha_s', 10, 'rendered_audio');
        """
    )
    db_conn.commit()
    
    # Generate subjective report
    report = generate_subjective_report(
        conn=db_conn,
        artifact_store=artifact_store,
        report_id="rpt_sub_test",
        run_id=run_id,
        abx_score=0.9,
        mos_score=4.5
    )
    
    # Assertions
    assert report.id == "rpt_sub_test"
    assert report.report_type == "subjective_report"
    assert report.summary_json["status"] == "generated"
    assert report.summary_json["abx_score"] == 0.9
    assert report.summary_json["mos_score"] == 4.5
    
    # Check artifact exists
    report_repo = ReportRepository(db_conn)
    rpt = report_repo.get_by_id("rpt_sub_test")
    assert rpt.artifact_id is not None
    art = artifact_store.get_artifact(rpt.artifact_id)
    assert os.path.exists(artifact_store.get_absolute_path(art))
