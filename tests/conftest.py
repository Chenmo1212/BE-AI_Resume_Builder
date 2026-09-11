"""
conftest.py — set required env vars before any app module is imported.
"""
import os
import sys
from unittest.mock import MagicMock

# Required for prompts.py
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
# MONGO_URI no longer required — backend is stateless
# os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/resume")

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
