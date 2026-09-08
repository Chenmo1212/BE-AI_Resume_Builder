"""
Tests for GET /tasks/<task_id>/progress SSE endpoint.
"""
import json
import pytest

from app import app as flask_app
from app.progress import push_event, cleanup_queue, task_progress_queues


@pytest.fixture(autouse=True)
def clean_queues():
    """Ensure no leftover queues between tests."""
    task_progress_queues.clear()
    yield
    task_progress_queues.clear()


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


# --- push_event unit tests ---

def test_push_event_creates_queue():
    """push_event creates a queue for unknown task_id."""
    push_event("t1", "parsing_job", 5, "running")
    assert "t1" in task_progress_queues
    q = task_progress_queues["t1"]
    item = q.get_nowait()
    raw_json = item.removeprefix("data: ").strip()
    data = json.loads(raw_json)
    assert data == {"step": "parsing_job", "pct": 5, "status": "running"}


def test_push_event_formats_sse_line():
    """Each event must start with 'data: ' and end with double newline."""
    push_event("t2", "done", 100, "done")
    q = task_progress_queues["t2"]
    item = q.get_nowait()
    assert item.startswith("data: ")
    assert item.endswith("\n\n")


def test_push_event_json_parseable():
    """The payload after 'data: ' must be valid JSON."""
    push_event("t3", "summary", 75, "running")
    q = task_progress_queues["t3"]
    item = q.get_nowait()
    raw_json = item.removeprefix("data: ").strip()
    data = json.loads(raw_json)
    assert data == {"step": "summary", "pct": 75, "status": "running"}


# --- SSE endpoint integration tests ---

def _collect_sse_events(response_data: bytes) -> list[dict]:
    """Parse raw SSE bytes into list of event dicts (skip keep-alive lines)."""
    events = []
    for line in response_data.decode().splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_sse_endpoint_streams_events_and_closes_on_done(client):
    """Endpoint streams queued events and closes after 'done'."""
    task_id = "task-sse-1"
    # Pre-populate the queue so the generator doesn't block
    push_event(task_id, "parsing_job", 5, "running")
    push_event(task_id, "done", 100, "done")

    response = client.get(f'/tasks/{task_id}/progress')

    assert response.status_code == 200
    assert 'text/event-stream' in response.content_type

    events = _collect_sse_events(response.data)
    assert len(events) == 2
    assert events[0] == {"step": "parsing_job", "pct": 5, "status": "running"}
    assert events[-1] == {"step": "done", "pct": 100, "status": "done"}


def test_sse_endpoint_closes_on_error_event(client):
    """Endpoint closes after receiving an error event and cleans up the queue."""
    task_id = "task-sse-2"
    push_event(task_id, "error", 0, "error")

    response = client.get(f'/tasks/{task_id}/progress')

    events = _collect_sse_events(response.data)
    assert events[-1]["status"] == "error"
    assert task_id not in task_progress_queues


def test_sse_endpoint_cleanup_queue_after_close(client):
    """Queue is removed from global dict after SSE stream ends."""
    task_id = "task-sse-3"
    push_event(task_id, "done", 100, "done")

    client.get(f'/tasks/{task_id}/progress')

    assert task_id not in task_progress_queues


def test_sse_content_type_header(client):
    """Response must have correct Content-Type."""
    task_id = "task-sse-4"
    push_event(task_id, "done", 100, "done")
    response = client.get(f'/tasks/{task_id}/progress')
    assert response.content_type.startswith("text/event-stream")
