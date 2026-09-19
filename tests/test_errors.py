import pytest
import json
from flask import Flask
from app.errors import (
    AppError,
    BadRequestError,
    NotFoundError,
    LLMConfigError,
    register_error_handlers,
)


@pytest.fixture
def error_app():
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    register_error_handlers(test_app)

    @test_app.route('/test-bad-request')
    def bad_request():
        raise BadRequestError("Invalid payload provided")

    @test_app.route('/test-not-found')
    def not_found():
        raise NotFoundError("Resume not found")

    @test_app.route('/test-llm-config')
    def llm_config():
        raise LLMConfigError("Invalid provider configuration")

    @test_app.route('/test-unhandled')
    def unhandled():
        raise RuntimeError("database host secret_pass_123")

    return test_app


def test_bad_request_handler(error_app):
    client = error_app.test_client()
    resp = client.get('/test-bad-request')
    data = json.loads(resp.data)
    assert resp.status_code == 400
    assert data['error'] == "Invalid payload provided"
    assert data['code'] == "BAD_REQUEST"


def test_not_found_handler(error_app):
    client = error_app.test_client()
    resp = client.get('/test-not-found')
    data = json.loads(resp.data)
    assert resp.status_code == 404
    assert data['error'] == "Resume not found"
    assert data['code'] == "NOT_FOUND"


def test_llm_config_handler(error_app):
    client = error_app.test_client()
    resp = client.get('/test-llm-config')
    data = json.loads(resp.data)
    assert resp.status_code == 400
    assert data['error'] == "Invalid provider configuration"
    assert data['code'] == "LLM_CONFIG_ERROR"


def test_unhandled_exception_sanitizes_and_returns_500(error_app):
    client = error_app.test_client()
    resp = client.get('/test-unhandled')
    data = json.loads(resp.data)
    assert resp.status_code == 500
    assert data['error'] == "Internal server error"
    assert data['code'] == "INTERNAL_ERROR"
    assert "secret_pass_123" not in resp.get_data(as_text=True)
