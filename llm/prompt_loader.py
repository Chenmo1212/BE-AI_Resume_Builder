from __future__ import annotations

import os
import yaml
import logging
from pathlib import Path
from typing import Optional
from pymongo import MongoClient
from langchain_core.prompts import ChatPromptTemplate

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
logger = logging.getLogger(__name__)


def _load_from_db(name: str) -> Optional[ChatPromptTemplate]:
    """Try to load a prompt from MongoDB. Returns None on any failure or miss."""
    try:
        uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/resume")
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        try:
            db_name = uri.rsplit("/", 1)[-1].split("?")[0] or "resume"
            doc = client[db_name]["prompt_templates"].find_one(
                {"name": name, "is_delete": False}
            )
            if doc is None:
                return None
            messages = [(msg["role"], msg["content"]) for msg in doc["messages"]]
            return ChatPromptTemplate.from_messages(messages)
        finally:
            client.close()
    except Exception:
        logger.warning("DB lookup failed for prompt '%s' — falling back to YAML", name)
        return None


def _load_from_yaml(name: str) -> ChatPromptTemplate:
    """Load a prompt from the prompts/ YAML directory.

    Raises:
        FileNotFoundError: If the named YAML file does not exist.
    """
    path = PROMPTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt '{name}' not found in DB or YAML files")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    messages = [(msg["role"], msg["content"]) for msg in data["messages"]]
    return ChatPromptTemplate.from_messages(messages)


def load_prompt(name: str) -> ChatPromptTemplate:
    """
    Load a named prompt. DB-first: reads from prompt_templates collection.
    Falls back to YAML file if DB has no record or is unreachable.

    Args:
        name: Prompt name (e.g. "section_highlighter")

    Returns:
        ChatPromptTemplate with messages and input_variables populated.

    Raises:
        FileNotFoundError: If neither DB nor YAML has the named prompt.
    """
    prompt = _load_from_db(name)
    if prompt is not None:
        return prompt
    return _load_from_yaml(name)
