import time

from flask import jsonify, request
from app import app
from app.models import ResumeManager, JobManager, TaskManager
import threading
import logging
from pipeline import Pipeline

# create logger
from prompts import Job_Post

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
        return jsonify({"error": str(e)}), 400


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
        return jsonify({"error": str(e)}), 400


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
        return jsonify({"error": str(e)}), 400


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
        return jsonify({"error": str(e)}), 400


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
        return jsonify({"error": str(e)}), 400


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
        return jsonify({"error": str(e)}), 400


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
        return jsonify({"error": str(e)}), 400


@app.route('/tasks/run', methods=['POST'])
def run_tasks():
    """
    data: {
    "resume": resume_json,
    "job_list": [{job1}, {job2}]
    }
    """
    try:
        data = request.get_json()
        if 'resume_id' not in data and 'resume' not in data:
            return jsonify({"error": str('Neither resume_id nor resume have been provided.')}), 400
        task_list = data.get("task_list", [])
        if not task_list:
            return jsonify({"error": str('Task_list has not been provided or task_list is empty.')}), 400
        resume_manager = ResumeManager()
        if 'resume_id' not in data:
            if not isinstance(data['resume'], dict):
                return jsonify({"error": str('Type of resume is not dict.')}), 400
            resume_id = resume_manager.create(data['resume'])
        else:
            resume_id = data['resume_id']

        task_ids = process_task_list(task_list, resume_id)

        return jsonify({"message": "Task created successfully", "task_ids": task_ids}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


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
        return jsonify({"error": str(e)}), 400


def process_batch(job_ids, task_ids, resume_id, update_part):
    print("job_ids:", job_ids)
    print("task_ids:", task_ids)
    task_manager = TaskManager()
    for job_id, task_id in zip(job_ids, task_ids):
        task_manager.update(task_id, {
            'status': 1,  # 0: waiting, 1: pending, 2: done
        })

        start_task(update_part, resume_id, job_id, task_id)


def process_task_list(task_list, resume_id):
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
        thread = threading.Thread(target=process_batch, args=(job_batch, task_batch, resume_id, update_part))
        thread.start()

    return task_ids


def parsing_job(raw_job, job_id):
    job_post = Job_Post(raw_job)
    parsed_job = job_post.parse_job_post(verbose=False)
    logger.info('parsed_job:', parsed_job)
    print("parsed_job: Done")
    manager = JobManager()
    manager.update(job_id, {
        **parsed_job,
        'status': 2,  # 0: waiting, 1: pending, 2: done
    })


def start_task(update_part, resume_id, job_id, task_id):
    start_time = time.time()
    resume_manager = ResumeManager()
    resume = resume_manager.get(resume_id)
    job_manager = JobManager()
    job = job_manager.get(job_id)

    ai_resume = Pipeline()
    ai_resume.set_job_text(job)
    ai_resume.set_raw_resume(resume)

    if update_part == "resume":
        ai_resume.main()
        resume = ai_resume.final_resume
    elif update_part == "experiences":
        experiences = ai_resume.update_experiences()
        resume = {
            **resume,
            "work": experiences
        }
    elif update_part == "summary":
        summary = ai_resume.update_summary()
        resume = {
            **resume,
            resume["basics"]["summary"]: summary
        }

    job_manager.update(job_id, {
        **ai_resume.parsed_job,
        'status': 2,  # 0: waiting, 1: pending, 2: done
    })

    new_resume_id = resume_manager.create({
        **resume,
        "is_raw": False,
        "raw_id": resume_id,
        "job_id": job_id
    })

    task_manager = TaskManager()
    task_manager.update(task_id, {
        'status': 2,  # 0: waiting, 1: pending, 2: done
        "time_used": time.time() - start_time,
        "new_resume_id": new_resume_id
    })
