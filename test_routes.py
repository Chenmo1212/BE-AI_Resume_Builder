import json
import pytest
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['MONGO_URI'] = 'mongodb://localhost:27017/resume_test'  # Use a test database
    with app.test_client() as client:
        yield client


def test_create_resume(client):
    data = {
        "basics": {},
        "skills": {},
        "work": [],
        "education": [],
        "activities": {},
        "volunteer": [],
        "awards": []
    }
    response = client.post('/resume', json=data)
    data = json.loads(response.data.decode('utf-8'))
    assert response.status_code == 201  # Check if the status code is 201 (Created)
    assert "inserted_id" in data  # Check if the response contains the inserted_id


def test_get_resume(client):
    response = client.get('/resume/12345')  # Replace with a valid resume ID
    assert response.status_code == 404  # Check if the status code is 404 (Not Found)


def test_update_resume(client):
    data = {"basics": {"name": "John Doe"}}
    response = client.put('/resume/12345', json=data)  # Replace with a valid resume ID
    assert response.status_code == 404  # Check if the status code is 404 (Not Found)


def test_delete_resume(client):
    response = client.delete('/resume/12345')  # Replace with a valid resume ID
    assert response.status_code == 404  # Check if the status code is 404 (Not Found)


def test_list_resumes(client):
    response = client.get('/resumes')
    assert response.status_code == 200  # Check if the status code is 200 (OK)
