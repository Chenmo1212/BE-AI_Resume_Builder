import queue
import json

# task_id -> Queue[str]  (str 为已格式化的 SSE data 行)
task_progress_queues: dict = {}
_queues_lock = __import__('threading').Lock()


def get_or_create_queue(task_id: str) -> queue.Queue:
    """Return existing queue for task_id, or create a new one."""
    with _queues_lock:
        if task_id not in task_progress_queues:
            task_progress_queues[task_id] = queue.Queue()
        return task_progress_queues[task_id]


def push_event(task_id: str, step: str, pct: int, status: str) -> None:
    """Format and enqueue a single SSE event for the given task_id."""
    q = get_or_create_queue(task_id)
    payload = json.dumps({"step": step, "pct": pct, "status": status})
    q.put(f"data: {payload}\n\n")


def cleanup_queue(task_id: str) -> None:
    """Remove queue after SSE connection is closed."""
    with _queues_lock:
        task_progress_queues.pop(task_id, None)
