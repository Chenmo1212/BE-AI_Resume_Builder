"""
conftest.py — set required env vars before any app module is imported.

IMPORTANT: these setdefault calls must run before *any* app module is imported,
including indirectly via test_chains.py.  The app's prompts.py calls
load_dotenv() at module level which injects real .env values (e.g. a real
DEEPSEEK_MODEL_NAME, LLM_PROVIDER) into os.environ.  load_dotenv() respects
already-set variables (override=False by default), so pre-seeding sentinel
values here prevents the .env from leaking into test_factory assertions that
use patch.dict to control the environment.
"""
import os
import sys
from unittest.mock import MagicMock

# --- Sentinel values: must be set BEFORE any app import triggers load_dotenv() ---
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
# Prevent real .env LLM config from leaking into factory / pipeline tests
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
os.environ.setdefault("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash")
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
