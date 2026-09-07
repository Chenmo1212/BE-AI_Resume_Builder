import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pipeline import Pipeline


def make_pipeline_with_mocks():
    """Return a Pipeline with mocked chains and pre-set parsed_job + raw_resume."""
    pipeline = Pipeline.__new__(Pipeline)
    pipeline.raw_job = "Software Engineer at Acme Corp"
    pipeline.raw_resume = {
        "basics": {"name": "Jane Doe", "summary": ""},
        "work": [{"name": "Acme", "unedited": True, "summary": "Built APIs", "titles": [{"startdate": "2020-01", "enddate": "current"}]}],
        "projects": [{"title": "Project A", "unedited": True, "summary": "ML pipeline", "skills": "Python"}],
        "skills": {"languages": [{"name": "Python"}], "practices": [{"name": "Agile"}]},
        "education": [],
        "activities": {},
    }
    pipeline.parsed_job = {
        "company": "Acme Corp",
        "job_title": "Software Engineer",
        "job_link": "https://example.com",
        "team": "",
        "job_summary": "Build software",
        "salary": "",
        "duties": ["Build REST APIs"],
        "qualifications": ["5 years Python"],
        "is_fully_remote": False,
        "technical_skills": ["Python", "REST"],
        "non_technical_skills": ["Communication"],
    }
    pipeline.llm_kwargs = {"model_name": "gpt-3.5-turbo"}
    pipeline.resume_builder = None
    pipeline.final_resume = {}
    pipeline.resume_filename = ""
    pipeline.folder = ""
    pipeline.root_path = "my_applications"
    pipeline.resume_json = ""
    return pipeline


def test_parallel_step_merges_all_three_results():
    """After _run_parallel_steps, resume_builder has experiences, projects, skills set."""
    pipeline = make_pipeline_with_mocks()

    # Mock the three chain builders to return predictable values
    mock_exp = [{"name": "Acme", "highlights": ["Led API development"]}]
    mock_proj = [{"title": "Project A", "highlights": ["Built ML pipeline"]}]
    mock_skills = [{"category": "Technical", "skills": ["Python"]}]

    with patch.object(pipeline, '_run_parallel_steps', new_callable=AsyncMock) as mock_parallel:
        async def set_results():
            pipeline.resume_builder = MagicMock()
            pipeline.resume_builder.experiences = mock_exp
            pipeline.resume_builder.projects = mock_proj
            pipeline.resume_builder.skills = mock_skills
        mock_parallel.side_effect = set_results

        asyncio.run(pipeline._run_parallel_steps())

    assert pipeline.resume_builder.experiences == mock_exp
    assert pipeline.resume_builder.projects == mock_proj
    assert pipeline.resume_builder.skills == mock_skills


def test_pipeline_sets_error_status_on_failure():
    """If start_task catches an exception, task status is set to -2."""
    from app.routes import start_task
    from unittest.mock import patch, MagicMock

    mock_task_manager = MagicMock()
    mock_resume_manager = MagicMock()
    mock_job_manager = MagicMock()
    mock_resume_manager.get.return_value = {"basics": {}, "work": [], "projects": [], "skills": {}}
    mock_job_manager.get.return_value = "Software Engineer at Acme"

    with patch('app.routes.TaskManager', return_value=mock_task_manager), \
         patch('app.routes.ResumeManager', return_value=mock_resume_manager), \
         patch('app.routes.JobManager', return_value=mock_job_manager), \
         patch('app.routes.Pipeline') as mock_pipeline_cls:
        mock_pipeline_cls.return_value.main.side_effect = Exception("LLM timeout")
        start_task("resume", "resume_id_123", "job_id_456", "task_id_789")

    # Check that status -2 was set
    update_calls = mock_task_manager.update.call_args_list
    final_call_kwargs = update_calls[-1][0][1]  # second positional arg of last call
    assert final_call_kwargs.get('status') == -2
