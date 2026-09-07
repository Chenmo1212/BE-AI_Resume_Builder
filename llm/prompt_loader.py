import yaml
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> ChatPromptTemplate:
    """
    Load a named prompt from the prompts/ YAML directory.

    Args:
        name: Filename stem (e.g. "section_highlighter" loads prompts/section_highlighter.yaml)

    Returns:
        ChatPromptTemplate with messages and input_variables populated.

    Raises:
        FileNotFoundError: If the named YAML file does not exist.
    """
    path = PROMPTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    messages = [(msg["role"], msg["content"]) for msg in data["messages"]]
    return ChatPromptTemplate.from_messages(messages)
