import json
import pytest
import requests
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
    print(data['inserted_id'])
    return data['inserted_id']


def test_get_resume(client):
    resume_id = test_create_resume(client)
    response = client.get(f'/resume/{resume_id}')  # Replace with a valid resume ID
    assert response.status_code == 200  # Check if the status code is 200 (OK)


def test_update_resume(client):
    resume_id = test_create_resume(client)
    data = {"basics": {"name": "John Doe"}}
    response = client.put(f'/resume/{resume_id}', json=data)  # Replace with a valid resume ID
    assert response.status_code == 200  # Check if the status code is 200 (OK)


def test_delete_resume(client):
    resume_id = test_create_resume(client)
    response = client.delete(f'/resume/{resume_id}')  # Replace with a valid resume ID
    assert response.status_code == 200  # Check if the status code is 200 (OK)


def test_list_resumes(client):
    response = client.get('/resumes')
    assert response.status_code == 200  # Check if the status code is 200 (OK)


def test_create_job(client):
    job_data = {
        "title": "Software Engineer",
        "description": "This is a job description.",
        "location": "New York",
    }

    response = client.post("/job", json=job_data)

    assert response.status_code == 201
    assert "inserted_id" in response.json

    return response.json["inserted_id"]


def test_get_job(client):
    job_id = test_create_job(client)
    response = client.get(f"/job/{job_id}")

    assert response.status_code == 200
    assert "title" in response.json
    assert "description" in response.json


def test_update_job(client):
    job_id = test_create_job(client)
    updated_job_data = {
        "description": "Updated job description.",
    }

    response = client.put(f"/job/{job_id}", json=updated_job_data)

    assert response.status_code == 200
    assert "Job updated successfully" in response.json["message"]


def test_delete_job(client):
    job_id = test_create_job(client)
    response = client.delete(f"/job/{job_id}")

    assert response.status_code == 200
    assert "Job deleted successfully" in response.json["message"]


def test_list_jobs(client):
    response = client.get("/jobs")

    assert response.status_code == 200
    assert isinstance(response.json, list)


if __name__ == '__main__':
    test_create_resume(client)
