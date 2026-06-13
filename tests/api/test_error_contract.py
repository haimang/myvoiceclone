import pytest
from fastapi.testclient import TestClient

from myvoiceclone.api.app import create_app
from myvoiceclone.api.dependencies import get_db


@pytest.mark.api
def test_http_errors_include_structured_error_and_legacy_detail(db_conn):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_conn
    client = TestClient(app)

    res = client.get("/api/recordings/missing")

    assert res.status_code == 404
    payload = res.json()
    assert payload["detail"] == "Recording not found"
    assert payload["error"]["code"] == "http_error"
    assert payload["error"]["message"] == "Recording not found"
    assert payload["error"]["trace_id"]
    assert res.headers["x-trace-id"] == payload["error"]["trace_id"]
