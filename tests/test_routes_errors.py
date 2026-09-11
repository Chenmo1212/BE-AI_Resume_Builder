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


def test_run_tasks_missing_resume_returns_400(client):
    """Missing resume field must return 400."""
    response = client.post('/tasks/run', json={"task_list": [{"id": "t1", "description": "job"}]})
    data = json.loads(response.data)
    assert response.status_code == 400
    assert data["error"] == "resume dict is required"


def test_run_tasks_resume_not_dict_returns_400(client):
    """resume field that is not a dict must return 400."""
    response = client.post('/tasks/run', json={"resume": "not-a-dict", "task_list": [{"id": "t1", "description": "job"}]})
    data = json.loads(response.data)
    assert response.status_code == 400
    assert data["error"] == "resume dict is required"


def test_run_tasks_empty_task_list_returns_400(client):
    """Empty task_list must return 400."""
    response = client.post('/tasks/run', json={"resume": {"basics": {}}, "task_list": []})
    data = json.loads(response.data)
    assert response.status_code == 400
