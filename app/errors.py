import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application exception."""
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "Internal server error", status_code: int = None, code: str = None, details=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.details = details

    def to_dict(self) -> dict:
        payload = {
            "error": self.message,
            "code": self.code,
        }
        if self.details is not None:
            payload["details"] = self.details
        return payload


class BadRequestError(AppError):
    status_code = 400
    code = "BAD_REQUEST"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class LLMConfigError(AppError):
    status_code = 400
    code = "LLM_CONFIG_ERROR"


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        return jsonify({
            "error": err.description,
            "code": "HTTP_ERROR",
        }), err.code

    @app.errorhandler(Exception)
    def handle_unhandled_exception(err: Exception):
        logger.error("Unhandled server exception: %s", err, exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "code": "INTERNAL_ERROR"
        }), 500
