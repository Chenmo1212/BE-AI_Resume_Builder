import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pipeline import Pipeline
from prompts import (
    format_list_as_string,
    format_prompt_inputs_as_strings,
)


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


def test_pipeline_uses_ai_config_model():
    """Pipeline must pass model from ai_config to create_llm."""
    ai_config = {"model": "gpt-4o", "temperature": 0.3, "sections": ["experience", "projects", "skills", "summary"]}

    with patch('pipeline.create_llm') as mock_create_llm:
        mock_create_llm.return_value = MagicMock()
        pipeline = Pipeline(ai_config=ai_config)
        pipeline._get_llm()
        mock_create_llm.assert_called_once()
        call_kwargs = mock_create_llm.call_args
        # model_name should be gpt-4o from ai_config
        all_args = str(call_kwargs)
        assert "gpt-4o" in all_args


def test_pipeline_skips_sections_not_in_ai_config():
    """If sections = ['skills'], experience and projects must not be rewritten."""
    pipeline = make_pipeline_with_mocks()
    pipeline.ai_config = {"model": "gpt-3.5-turbo", "temperature": 0.7, "sections": ["skills"]}
    pipeline.resume_builder = {
        "experiences_raw": [{"name": "Acme", "unedited": True, "summary": "Built APIs", "titles": []}],
        "projects_raw": [{"title": "Proj", "unedited": True, "summary": "ML work", "skills": "Python"}],
        "experiences": None,
        "projects": None,
        "skills": None,
        "summary_raw": "",
    }

    called_rewrites = []

    async def mock_rewrite_exp(exp):
        called_rewrites.append("experience")
        return exp

    async def mock_rewrite_proj(proj):
        called_rewrites.append("projects")
        return proj

    async def mock_extract_skills():
        called_rewrites.append("skills")
        return [{"category": "Technical", "skills": ["Python"]}]

    with patch.object(pipeline, '_rewrite_experience_async', side_effect=mock_rewrite_exp), \
         patch.object(pipeline, '_rewrite_project_async', side_effect=mock_rewrite_proj), \
         patch.object(pipeline, '_extract_skills_async', side_effect=mock_extract_skills):
        asyncio.run(pipeline._run_parallel_steps())

    assert "experience" not in called_rewrites
    assert "projects" not in called_rewrites
    assert "skills" in called_rewrites


def test_pipeline_default_ai_config_runs_all_sections():
    """With no ai_config, all sections must be processed."""
    pipeline = make_pipeline_with_mocks()
    pipeline.ai_config = None  # will be set in __init__ as {}, default = all sections
    pipeline.resume_builder = {
        "experiences_raw": [{"name": "Acme", "unedited": True, "summary": "Built APIs", "titles": []}],
        "projects_raw": [{"title": "Proj", "unedited": True, "summary": "ML work", "skills": "Python"}],
        "experiences": None,
        "projects": None,
        "skills": None,
        "summary_raw": "",
    }

    called_rewrites = []

    async def mock_rewrite_exp(exp):
        called_rewrites.append("experience")
        return exp

    async def mock_rewrite_proj(proj):
        called_rewrites.append("projects")
        return proj

    async def mock_extract_skills():
        called_rewrites.append("skills")
        return []

    with patch.object(pipeline, '_rewrite_experience_async', side_effect=mock_rewrite_exp), \
         patch.object(pipeline, '_rewrite_project_async', side_effect=mock_rewrite_proj), \
         patch.object(pipeline, '_extract_skills_async', side_effect=mock_extract_skills):
        asyncio.run(pipeline._run_parallel_steps())

    assert "experience" in called_rewrites
    assert "projects" in called_rewrites
    assert "skills" in called_rewrites
