from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load the appropriate configuration based on the environment
# if app.env == 'production':
#     app.config.from_object('config_production')
# else:
app.config.from_object('config_development')

app.debug = True

mongo = None
try:
    from flask_pymongo import PyMongo as _PyMongo
    mongo = _PyMongo(app)
except Exception:
    import logging as _log
    _log.getLogger(__name__).warning("MongoDB unavailable — running in stateless mode")

# Auto-seed prompt templates from YAML files on first startup
try:
    from llm.seed_prompts import seed_prompt_templates
    seed_prompt_templates()
except Exception:
    pass  # Mongo may be absent

from app import routes
