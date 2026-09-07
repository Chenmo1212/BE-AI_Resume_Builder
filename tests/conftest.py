"""
conftest.py — set required env vars and mock heavy dependencies
before any app module is imported.
"""
import os
import sys
from unittest.mock import MagicMock

# Must be set before importing app (prompts.py raises EnvironmentError otherwise)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/resume")

# Import pymongo/flask_pymongo early so bson is loaded as a real package
# (bson is bundled with pymongo; stubbing it would break pymongo itself).
import pymongo  # noqa: E402
import flask_pymongo  # noqa: E402
flask_pymongo.PyMongo = MagicMock(return_value=MagicMock())

# Stub out optional/heavy packages not installed in the test venv
# but imported at module level by application code.
for _mod in (
    "ruamel",
    "ruamel.yaml",
    "ruamel.yaml.compat",
    "ruamel.yaml.error",
    "jinja2",
    "pathvalidate",
    "dateutil",
    "dateutil.relativedelta",
    "dateutil._parser",
    "langchain",
    "langchain.cache",
    "langchain.chains",
    "langchain.chains.openai_functions",
    "langchain.chat_models",
    "langchain.prompts",
    "langchain.schema",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
