from __future__ import annotations

import yaml
import logging
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
logger = logging.getLogger(__name__)


def _load_from_yaml(name: str) -> ChatPromptTemplate:
    """Load a prompt from the prompts/ YAML directory.

    Raises:
        FileNotFoundError: If the named YAML file does not exist.
    """
    path = PROMPTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt '{name}' not found in YAML files")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    messages = [(msg["role"], msg["content"]) for msg in data["messages"]]
    return ChatPromptTemplate.from_messages(messages)


def load_prompt(name: str) -> ChatPromptTemplate:
    """
    Load a named prompt from the prompts/ YAML directory.

    Args:
        name: Prompt name (e.g. "section_highlighter")

    Returns:
        ChatPromptTemplate with messages and input_variables populated.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
    """
    return _load_from_yaml(name)
