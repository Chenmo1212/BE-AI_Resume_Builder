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
            'raw': data,
            'status': 0,  # 0: waiting, 1:pending, 2: done
        })
        return jsonify({"message": "Job created successfully", "inserted_id": str(job_id)}), 201
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
    return jsonify(jobs)


@app.route('/task', methods=['POST'])
def add_task():
    try:
        data = request.get_json()

        if 'resume_id' not in data and 'resume' not in data:
            return jsonify({"error": str('Neither resume_id nor resume have been provided.')}), 400
        if 'job_id' not in data and 'job_text' not in data:
            return jsonify({"error": str('Neither job_id nor job_text have been provided.')}), 400

        resume_manager = ResumeManager()
        if 'resume_id' not in data:
            if not isinstance(data['resume'], dict):
                return jsonify({"error": str('Type of resume is not dict.')}), 400
            resume_id = resume_manager.create(data['resume'])
        else:
            resume_id = data['resume_id']

        job_manager = JobManager()
        if 'job_id' not in data:
            job_id = job_manager.create({'raw': data['job_text']})
        else:
            job_id = data['job_id']

        task_manager = TaskManager()
        task_id = task_manager.create({
            'job_id': job_id,
            'resume_id': resume_id,
            'status': 1,  # 0: waiting, 1: pending, 2: done
            'content': "resume"
        })

        task = threading.Thread(target=start_task, args=(resume_id, job_id, task_id))
        task.start()

        return jsonify({"message": "Task created successfully", "inserted_id": str(task_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


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


def start_task(resume_id, job_id, task_id):
    start_time = time.time()
    resume_manager = ResumeManager()
    resume = resume_manager.get(resume_id)
    job_manager = JobManager()
    job = job_manager.get(job_id)

    ai_resume = Pipeline()
    ai_resume.set_job_text(job)
    ai_resume.set_raw_resume(resume)
    ai_resume.main()

    job_manager.update(job_id, {
        **ai_resume.parsed_job,
        'status': 2,  # 0: waiting, 1: pending, 2: done
    })

    resume_manager.create({
        **ai_resume.final_resume,
        "is_raw": False,
        "raw_id": resume_id,
        "job_id": job_id
    })
