import pytest
from fastapi.testclient import TestClient
from myvoiceclone.api.app import create_app
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.domain.entities import Dataset

@pytest.fixture
def api_client(db_conn):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_conn
    return TestClient(app)

@pytest.mark.api
def test_recordings_endpoints(api_client, db_conn):
    # Pre-populate recording
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_route_1', 'uri_1', 'sha_route_1', 5.0, 16000, 1, 'processed');
        """
    )
    db_conn.commit()

    # GET all
    res = api_client.get("/api/recordings")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["id"] == "rec_route_1"

    # GET single
    res2 = api_client.get("/api/recordings/rec_route_1")
    assert res2.status_code == 200
    assert res2.json()["source_uri"] == "uri_1"

    # POST create ingest job
    res3 = api_client.post("/api/recordings?filepath=fake_file.wav")
    assert res3.status_code == 200
    assert res3.json()["name"] == "ingest"
    assert res3.json()["status"] == "pending"

@pytest.mark.api
def test_segments_endpoints(api_client, db_conn):
    # Pre-populate data
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_seg', 'uri_seg', 'sha_seg', 10.0, 16000, 1, 'processed');
        """
    )
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, quality_score)
        VALUES ('seg_route_1', 'rec_seg', 0.0, 4.0, 'processed', 0.85);
        """
    )
    db_conn.commit()

    # GET list by recording
    res = api_client.get("/api/segments?recording_id=rec_seg")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["id"] == "seg_route_1"

    # PATCH review status
    payload = {"status_to": "keep", "reason": "good audio quality", "reviewer": "admin"}
    res2 = api_client.patch("/api/segments/seg_route_1/review", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "keep"

    # Check review log entry was saved
    cursor = db_conn.cursor()
    cursor.execute("SELECT status_to, reason, reviewer FROM segment_reviews WHERE segment_id = 'seg_route_1';")
    row = cursor.fetchone()
    assert row["status_to"] == "keep"
    assert row["reason"] == "good audio quality"
    assert row["reviewer"] == "admin"

@pytest.mark.api
def test_datasets_endpoints(api_client, db_conn, artifact_store):
    # Pre-populate segments with clean artifact
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_ds', 'uri_ds', 'sha_ds', 10.0, 16000, 1, 'processed');
        """
    )
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, quality_score, cleaned_artifact_id)
        VALUES ('seg_ds_1', 'rec_ds', 0.0, 5.0, 'keep', 0.8, 'art_clean_ds');
        """
    )
    # Insert clean artifact
    db_conn.execute("INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type) VALUES ('art_clean_ds', 'clean.wav', 'cleaned/clean.wav', 'sha_c', 10, 'cleaned');")
    db_conn.commit()

    # POST create dataset
    payload = {"name": "first-dataset", "filter_json": {"min_quality_score": 0.7}}
    res = api_client.post("/api/datasets", json=payload)
    assert res.status_code == 200
    ds_id = res.json()["id"]
    assert res.json()["name"] == "first-dataset"
    assert res.json()["status"] == "active"
    
    # POST freeze dataset
    res2 = api_client.post(f"/api/datasets/{ds_id}/freeze")
    assert res2.status_code == 200
    assert res2.json()["status"] == "frozen"
    assert res2.json()["manifest_sha256"] is not None

@pytest.mark.api
def test_jobs_endpoints(api_client, db_conn):
    # Pre-populate job
    db_conn.execute(
        """
        INSERT INTO jobs (id, name, status, payload_json)
        VALUES ('job_route_1', 'ingest', 'pending', '{"filepath": "dummy.wav"}');
        """
    )
    db_conn.commit()

    # GET list
    res = api_client.get("/api/jobs")
    assert res.status_code == 200
    assert len(res.json()) == 1

    # GET single
    res2 = api_client.get("/api/jobs/job_route_1")
    assert res2.status_code == 200
    assert res2.json()["name"] == "ingest"
