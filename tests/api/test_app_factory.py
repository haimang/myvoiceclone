import pytest
from fastapi.testclient import TestClient
from myvoiceclone.api.app import create_app
from myvoiceclone.api.dependencies import get_db

@pytest.mark.api
def test_app_factory_health():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}

@pytest.mark.api
def test_app_factory_db_override():
    app = create_app()
    
    # Test override dependency
    override_triggered = False
    def mock_db():
        nonlocal override_triggered
        override_triggered = True
        # Return a dummy connection or object
        return None
        
    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app)
    
    # Send a request to an endpoint that requires db
    try:
        client.get("/api/recordings")
    except Exception:
        # It might throw if mock_db returns None instead of a valid connection,
        # but that is fine since we just want to prove mock_db is called.
        pass
        
    assert override_triggered is True
