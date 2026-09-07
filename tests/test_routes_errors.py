import pytest
import json
from unittest.mock import patch, MagicMock
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


def test_insert_resume_error_is_generic(client):
    """Error response must not leak exception details."""
    with patch('app.routes.ResumeManager') as mock_mgr:
        mock_mgr.return_value.create.side_effect = Exception("db connection string: mongodb://user:pass@host")
        response = client.post('/resume', json={"basics": {}})
        data = json.loads(response.data)
        assert response.status_code == 500
        assert data["error"] == "Internal server error"
        assert "mongodb" not in data["error"]
        assert "user" not in data["error"]


def test_insert_job_error_is_generic(client):
    with patch('app.routes.JobManager') as mock_mgr:
        mock_mgr.return_value.create.side_effect = Exception("secret detail")
        response = client.post('/job', json={})
        data = json.loads(response.data)
        assert response.status_code == 500
        assert data["error"] == "Internal server error"
        assert "secret detail" not in data["error"]
