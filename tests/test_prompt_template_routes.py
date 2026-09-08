import pytest
from unittest.mock import patch, MagicMock


SAMPLE_TEMPLATES = [
    {
        "id": "64a1b2c3d4e5f60000100001",
        "name": "section_highlighter",
        "description": "Highlights resume sections",
        "version": 1,
        "messages": [
            {"role": "system", "content": "You are an expert."},
            {"role": "human", "content": "Review {section}"},
        ],
    },
]

VALID_MESSAGES = [
    {"role": "system", "content": "Updated system message"},
    {"role": "human", "content": "Updated {section}"},
]


@pytest.fixture()
def client():
    import os
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    os.environ.setdefault("MONGO_URI", "mongodb://localhost/test")
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@patch("app.routes.PromptTemplateManager")
def test_get_prompt_templates_returns_list(mock_mgr_cls, client):
    mock_mgr_cls.return_value.list_all.return_value = SAMPLE_TEMPLATES
    resp = client.get("/prompt-templates")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "section_highlighter"


@patch("app.routes.PromptTemplateManager")
def test_get_prompt_templates_empty_list(mock_mgr_cls, client):
    mock_mgr_cls.return_value.list_all.return_value = []
    resp = client.get("/prompt-templates")
    assert resp.status_code == 200
    assert resp.get_json() == []


@patch("app.routes.PromptTemplateManager")
def test_put_prompt_template_success(mock_mgr_cls, client):
    mock_mgr = mock_mgr_cls.return_value
    mock_mgr.get.return_value = SAMPLE_TEMPLATES[0]
    mock_mgr.update_with_history.return_value = 2

    resp = client.put(
        "/prompt-templates/64a1b2c3d4e5f60000100001",
        json={"messages": VALID_MESSAGES},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["version"] == 2
    assert "updated" in data["message"].lower()


@patch("app.routes.PromptTemplateManager")
def test_put_prompt_template_missing_messages(mock_mgr_cls, client):
    resp = client.put(
        "/prompt-templates/64a1b2c3d4e5f60000100001",
        json={"wrong_key": "value"},
    )
    assert resp.status_code == 400


@patch("app.routes.PromptTemplateManager")
def test_put_prompt_template_invalid_role(mock_mgr_cls, client):
    resp = client.put(
        "/prompt-templates/64a1b2c3d4e5f60000100001",
        json={"messages": [{"role": "bot", "content": "hello"}]},
    )
    assert resp.status_code == 400


@patch("app.routes.PromptTemplateManager")
def test_put_prompt_template_empty_messages(mock_mgr_cls, client):
    resp = client.put(
        "/prompt-templates/64a1b2c3d4e5f60000100001",
        json={"messages": []},
    )
    assert resp.status_code == 400


@patch("app.routes.PromptTemplateManager")
def test_put_prompt_template_not_found(mock_mgr_cls, client):
    mock_mgr_cls.return_value.get.return_value = None
    resp = client.put(
        "/prompt-templates/64a1b2c3d4e5f60000100001",
        json={"messages": VALID_MESSAGES},
    )
    assert resp.status_code == 404
