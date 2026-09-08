from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load the appropriate configuration based on the environment
# if app.env == 'production':
#     app.config.from_object('config_production')
# else:
app.config.from_object('config_development')

app.debug = True

mongo = PyMongo(app)

# Auto-seed prompt templates from YAML files on first startup
try:
    from llm.seed_prompts import seed_prompt_templates
    seed_prompt_templates()
except Exception:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "prompt_templates seed failed (DB may be unavailable) — YAML fallback will be used",
        exc_info=False,
    )

from app import routes
