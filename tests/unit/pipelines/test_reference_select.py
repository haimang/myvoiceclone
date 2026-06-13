import pytest

from myvoiceclone.pipelines.reference_select import select_reference_artifact


@pytest.mark.unit
def test_reference_selector_returns_traceable_cleaned_artifact(db_conn, artifact_store):
    artifact = artifact_store.create_artifact(
        name="cleaned.wav",
        content=b"cleaned audio",
        artifact_type="cleaned",
        metadata_json={"adapter_mode": "real", "tool": "demucs"},
    )
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_ref', 'uri_ref', 'sha_ref', 5.0, 16000, 1, 'processed');
        """
    )
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, cleaned_artifact_id, transcript)
        VALUES ('seg_ref', 'rec_ref', 0.0, 4.0, 'transcribed', ?, 'hello reference');
        """,
        (artifact.id,),
    )
    db_conn.commit()

    selected = select_reference_artifact(db_conn, artifact_store)

    assert selected["segment_id"] == "seg_ref"
    assert selected["artifact_id"] == artifact.id
    assert selected["sha256"] == artifact.sha256
    assert selected["duration_sec"] == 4.0
    assert selected["metadata_json"]["tool"] == "demucs"


@pytest.mark.unit
def test_reference_selector_rejects_missing_lineage(db_conn, artifact_store):
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_ref_empty', 'uri_ref_empty', 'sha_ref_empty', 5.0, 16000, 1, 'processed');
        """
    )
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, transcript)
        VALUES ('seg_ref_empty', 'rec_ref_empty', 0.0, 4.0, 'transcribed', 'no artifact');
        """
    )
    db_conn.commit()

    with pytest.raises(ValueError, match="No eligible reference audio artifact"):
        select_reference_artifact(db_conn, artifact_store)
