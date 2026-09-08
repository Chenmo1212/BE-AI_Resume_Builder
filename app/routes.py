import time
import queue
import json as _json

from flask import jsonify, request, Response, stream_with_context
from app import app
from app.models import ResumeManager, JobManager, TaskManager, PromptTemplateManager
import threading
import logging
from pipeline import Pipeline
from app.progress import push_event, get_or_create_queue, cleanup_queue

logger = logging.getLogger(__name__)


@app.route('/', methods=['GET'])
def index():
    return "hello world"


# Resume APIs
@app.route('/resume', methods=['POST'])
def insert_resume():
    try:
        data = request.get_json()
        manager = ResumeManager()
        resume_id = manager.create(data)
        return jsonify({"message": "Resume created successfully", "inserted_id": str(resume_id)}), 201
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/resume/<resume_id>', methods=['GET'])
def get_resume(resume_id):
    manager = ResumeManager()
    resume = manager.get(resume_id)
    if resume:
        return jsonify(resume)
    return jsonify({"error": "Resume not found"}), 404


@app.route('/resume/<resume_id>', methods=['PUT'])
def update_resume(resume_id):
    try:
        data = request.get_json()
        manager = ResumeManager()
        modified_count = manager.update(resume_id, data)
        if modified_count > 0:
            return jsonify({"message": "Resume updated successfully"}), 200
        return jsonify({"error": "Resume not found or already deleted"}), 404
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/resume/<resume_id>', methods=['DELETE'])
def delete_resume(resume_id):
    manager = ResumeManager()
    modified_count = manager.delete(resume_id)
    if modified_count > 0:
        return jsonify({"message": "Resume deleted successfully"}), 200
    return jsonify({"error": "Resume not found or already deleted"}), 404


@app.route('/resumes', methods=['GET'])
def list_resumes():
    manager = ResumeManager()
    resumes = manager.list()
    return jsonify(resumes)


# Job APIs
@app.route('/job', methods=['POST'])
def insert_job():
    try:
        data = request.get_json()
        manager = JobManager()
        job_id = manager.create({
            'raw': data.get('raw', ''),
            'company': data.get('company', ''),
            'title': data.get('title', ''),
            'link': data.get('link', ''),
            'status': 0,  # 0: waiting, 1:pending, 2: done
        })
        return jsonify({"message": "Job created successfully", "job_id": str(job_id)}), 201
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/job/<job_id>', methods=['GET'])
def get_job(job_id):
    manager = JobManager()
    job = manager.get(job_id)
    if job:
        return jsonify(job)
    return jsonify({"error": "Job not found"}), 404


@app.route('/job/<job_id>', methods=['PUT'])
def update_job(job_id):
    try:
        data = request.get_json()
        manager = JobManager()
        modified_count = manager.update(job_id, data)
        if modified_count > 0:
            return jsonify({"message": "Job updated successfully"}), 200
        return jsonify({"error": "Job not found or already deleted"}), 404
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/job/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    manager = JobManager()
    modified_count = manager.delete(job_id)
    if modified_count > 0:
        return jsonify({"message": "Job deleted successfully"}), 200
    return jsonify({"error": "Job not found or already deleted"}), 404


@app.route('/jobs', methods=['GET'])
def list_jobs():
    manager = JobManager()
    jobs = manager.list()
    return jsonify({"message": "Jobs queried successfully", "jobs": jobs})


@app.route('/task', methods=['POST'])
def add_task():
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        job_text = data.get('job_text')
        resume_id = data.get('resume_id')
        resume = data.get('resume')

        if not job_id and not job_text:
            return jsonify({"error": "Neither job_id nor job_text have been provided."}), 400

        job_manager = JobManager()
        task_manager = TaskManager()
        resume_manager = ResumeManager()

        if not job_id:
            job_id = job_manager.create({'raw': job_text})

        init_task_data = {
            'job_id': job_id,
            'raw_resume_id': "",
            'status': -1,  # -1: default, 0: waiting, 1: pending, 2: done
            'content': "resume"
        }

        if not resume_id and not resume:
            task = task_manager.query(job_id=job_id)
            if task:
                return jsonify({"message": "Exist same task!", "id": str(task['id'])}), 201
            else:
                task_id = task_manager.create(init_task_data)
                return jsonify({"message": "Empty task created successfully", "id": str(task_id)}), 201

        if not resume_id:
            if not isinstance(resume, dict):
                return jsonify({"error": "Type of resume is not dict."}), 400
            resume_id = resume_manager.create(resume)
        init_task_data['raw_resume_id'] = resume_id

        task = task_manager.query(job_id=job_id)
        if task:
            return jsonify({"message": "Exist same task!", "id": str(task['id'])}), 201

        task_id = task_manager.create(init_task_data)
        return jsonify({"message": "Task created successfully", "id": str(task_id)}), 201

    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/task/<task_id>', methods=['PUT'])
def update_task(task_id):
    try:
        data = request.get_json()
        task_manager = TaskManager()
        task = task_manager.get(task_id)
        if not task:
            return jsonify({"message": "Can not find any document from " + task_id}), 400
        if 'id' in data:
            del data['id']
        task_manager.update(task_id, {**task, **data})
        return jsonify({"message": "Task updated successfully"}), 201
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/tasks', methods=['POST'])
def get_tasks():
    """
    data: {
    "job_ids": ['123', '456']
    }
    """
    try:
        data = request.get_json()
        tasks = []

        task_manager = TaskManager()
        job_manager = JobManager()
        resume_manager = ResumeManager()
        job_ids = data.get('job_ids')
        # Batch query tasks and related work
        tasks_dict = {}

        jobs_dict = {str(job['id']): job for job in job_manager.get_by_ids(job_ids)}
        for job_id in job_ids:
            task = task_manager.query(job_id=job_id)
            if task:
                tasks_dict[job_id] = task

        # Query resumes related to tasks in batches
        resume_ids = set(task['new_resume_id'] for task in tasks_dict.values() if task.get("status") == 2)
        resumes_dict = {str(resume['id']): resume for resume in resume_manager.get_by_ids(resume_ids)}
        # Build results
        for job_id in job_ids:
            task = tasks_dict.get(job_id)
            job = jobs_dict.get(job_id)
            if task and job:
                resume = resumes_dict.get(task.get('new_resume_id'))
                tasks.append({
                    **task,
                    "title": job.get('title'),
                    "company": job.get('company'),
                    "link": job.get('link'),
                    "resume": resume
                })
            else:
                tasks.append({"task": task, "job": job})
        return jsonify({"message": "Task queried successfully", "data": tasks}), 201
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/tasks/run', methods=['POST'])
def run_tasks():
    """
    data: {
    "resume": resume_json,
    "job_list": [{job1}, {job2}],
    "ai_config": {"model": "gpt-4o", "temperature": 0.7, "sections": ["experience", "projects", "skills", "summary"]}
    }
    """
    try:
        data = request.get_json()
        if 'resume_id' not in data and 'resume' not in data:
            return jsonify({"error": "Neither resume_id nor resume have been provided."}), 400
        task_list = data.get("task_list", [])
        if not task_list:
            return jsonify({"error": "Task_list has not been provided or task_list is empty."}), 400
        resume_manager = ResumeManager()
        if 'resume_id' not in data:
            if not isinstance(data['resume'], dict):
                return jsonify({"error": "Type of resume is not dict."}), 400
            resume_id = resume_manager.create(data['resume'])
        else:
            resume_id = data['resume_id']

        # Extract optional AI configuration from request
        ai_config = data.get("ai_config") or {}

        task_ids = process_task_list(task_list, resume_id, ai_config=ai_config)

        return jsonify({"message": "Task created successfully", "task_ids": task_ids}), 201
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/tasks/results', methods=['POST'])
def check_tasks_status():
    """
    data: {
    "task_ids": ["001", "002"]
    }
    """
    try:
        done = 2  # 0: waiting, 1: pending, 2: done
        data = request.get_json()
        task_ids = data.get("task_ids", [])
        if not task_ids:
            return jsonify({"error": str('task_ids is empty.')}), 400

        task_manager = TaskManager()
        resume_manager = ResumeManager()
        tasks = []
        for task_id in task_ids:
            if not task_id:
                tasks.append(None)
                continue
            task = task_manager.get(task_id)
            if not task:
                tasks.append(None)
                continue

            resume = {}
            if task["status"] == done:
                resume = resume_manager.get(task["new_resume_id"])
            tasks.append({
                **task,
                'resume': resume
            })

        return jsonify({"message": "Task queried successfully", "tasks": tasks}), 201
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


def process_batch(job_ids, task_ids, resume_id, update_part, ai_config: dict = None):
    logger.info("job_ids: %s", job_ids)
    logger.info("task_ids: %s", task_ids)
    task_manager = TaskManager()
    for job_id, task_id in zip(job_ids, task_ids):
        task_manager.update(task_id, {
            'status': 1,  # 0: waiting, 1: pending, 2: done
        })
        start_task(update_part, resume_id, job_id, task_id, ai_config=ai_config)


def process_task_list(task_list, resume_id, ai_config: dict = None):
    update_part = 'resume'
    batch_size = 5
    num_tasks = len(task_list)
    num_batches = (num_tasks + batch_size - 1) // batch_size

    task_manager = TaskManager()
    job_manager = JobManager()
    job_ids = []
    task_ids = []
    for task in task_list:
        if 'jobId' not in task:
            job_id = job_manager.create({'raw': task['description']})
        else:
            job_id = task['jobId']
        job_ids.append(job_id)
        task_id = task['id']
        task_manager.update(task_id, {
            'job_id': job_id,
            'raw_resume_id': resume_id,
            'status': 0,  # 0: waiting, 1: pending, 2: done
            'content': task.get('content') or update_part
        })
        task_ids.append(task_id)

    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, num_tasks)
        job_batch = job_ids[start_idx:end_idx]
        task_batch = task_ids[start_idx:end_idx]

        # Create a thread to process the batch asynchronously
        thread = threading.Thread(target=process_batch, args=(job_batch, task_batch, resume_id, update_part, ai_config))
        thread.start()

    return task_ids


def parsing_job(raw_job, job_id):
    ai_resume = Pipeline()
    ai_resume.set_job_text(raw_job)
    ai_resume.read_and_parse_job()
    parsed_job = ai_resume.parsed_job
    logger.info('parsed_job:', parsed_job)
    print("parsed_job: Done")
    manager = JobManager()
    manager.update(job_id, {
        **parsed_job,
        'status': 2,  # 0: waiting, 1: pending, 2: done
    })


def start_task(update_part, resume_id, job_id, task_id, ai_config: dict = None):
    start_time = time.time()
    resume_manager = ResumeManager()
    resume = resume_manager.get(resume_id)
    job_manager = JobManager()
    job = job_manager.get(job_id)
    task_manager = TaskManager()

    try:
        push_event(task_id, "parsing_job", 5, "running")
        ai_resume = Pipeline(ai_config=ai_config)
        ai_resume.set_job_text(job["raw"])
        ai_resume.set_raw_resume(resume)
        ai_resume.read_and_parse_job()
        push_event(task_id, "parsing_job", 20, "running")

        ai_resume.read_resume()
        push_event(task_id, "reading_resume", 25, "running")

        if update_part == "resume":
            push_event(task_id, "parallel_steps", 30, "running")
            import asyncio as _asyncio
            _asyncio.run(ai_resume._run_parallel_steps())
            push_event(task_id, "parallel_steps", 70, "running")

            push_event(task_id, "summary", 75, "running")
            ai_resume.update_summary()
            push_event(task_id, "summary", 85, "running")

            push_event(task_id, "improving", 88, "running")
            ai_resume.improve_final_resume()
            push_event(task_id, "improving", 90, "running")

            push_event(task_id, "finalizing", 92, "running")
            ai_resume.generate_resume_yaml()
            ai_resume.generate_json()
            resume = ai_resume.final_resume
            push_event(task_id, "finalizing", 95, "running")

        elif update_part == "experiences":
            ai_resume.update_experiences()
            resume = {**resume, "work": ai_resume.resume_builder["experiences"]}
            push_event(task_id, "finalizing", 90, "running")

        elif update_part == "summary":
            ai_resume.update_summary()
            resume = {**resume, "basics": {**resume["basics"], "summary": ai_resume.resume_builder["summary"]}}
            push_event(task_id, "finalizing", 90, "running")

        job_manager.update(job_id, {**ai_resume.parsed_job, 'status': 2})

        new_resume_id = resume_manager.create({
            **resume,
            "is_raw": False,
            "raw_id": resume_id,
            "job_id": job_id,
        })

        task_manager.update(task_id, {
            'status': 2,
            "time_used": time.time() - start_time,
            "new_resume_id": new_resume_id,
        })
        push_event(task_id, "done", 100, "done")

    except Exception:
        logger.error("Pipeline failed for task %s", task_id, exc_info=True)
        task_manager.update(task_id, {
            'status': -2,
            'error': 'Pipeline failed',
        })
        push_event(task_id, "error", 0, "error")


@app.route('/tasks/<task_id>/progress', methods=['GET'])
def task_progress(task_id):
    """SSE endpoint — streams progress events for a single task.

    Events: data: {"step": str, "pct": int, "status": "running"|"done"|"error"}
    Connection closes when status == "done" or "error".
    """
    q = get_or_create_queue(task_id)

    def generate():
        try:
            while True:
                try:
                    # Block up to 30 s; send a keep-alive comment if nothing arrives
                    event = q.get(timeout=30)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                yield event
                # Parse status to decide whether to close
                try:
                    data = _json.loads(event.removeprefix("data: ").strip())
                    if data.get("status") in ("done", "error"):
                        break
                except Exception:
                    pass
        finally:
            cleanup_queue(task_id)

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


# Prompt Template APIs

_VALID_ROLES = {"system", "human", "ai"}


def _validate_messages(messages) -> str:
    """Returns an error string if messages are invalid, else empty string."""
    if not isinstance(messages, list) or len(messages) == 0:
        return "messages must be a non-empty list"
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            return f"messages[{i}] must be an object"
        if msg.get("role") not in _VALID_ROLES:
            return f"messages[{i}].role must be one of: {', '.join(sorted(_VALID_ROLES))}"
        if not isinstance(msg.get("content"), str) or not msg["content"].strip():
            return f"messages[{i}].content must be a non-empty string"
    return ""


@app.route("/prompt-templates", methods=["GET"])
def list_prompt_templates():
    try:
        manager = PromptTemplateManager()
        templates = manager.list_all()
        return jsonify(templates), 200
    except Exception:
        logger.error("Failed to list prompt templates", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/prompt-templates/<template_id>", methods=["PUT"])
def update_prompt_template(template_id):
    try:
        data = request.get_json() or {}
        messages = data.get("messages")
        error = _validate_messages(messages)
        if error:
            return jsonify({"error": error}), 400

        manager = PromptTemplateManager()
        existing = manager.get(template_id)
        if not existing:
            return jsonify({"error": "Prompt template not found"}), 404

        new_version = manager.update_with_history(template_id, messages)
        logger.info("Prompt template '%s' updated to version %d", existing.get("name"), new_version)
        return jsonify({"message": "Prompt template updated", "version": new_version}), 200
    except Exception:
        logger.error("Failed to update prompt template", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
