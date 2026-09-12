from __future__ import annotations

import os
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from pymongo import MongoClient

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_DESCRIPTIONS = {
    "section_highlighter": "Highlights resume sections matching the job posting",
    "skills_matcher": "Extracts skills from resume matching job requirements",
    "summary_writer": "Writes a professional summary tailored to the job",
    "improver": "Critiques the resume and suggests improvements",
    "reviewer": "Internal quality reviewer — not user-editable",
}

_YAML_NAMES = ["section_highlighter", "skills_matcher", "summary_writer", "improver", "reviewer"]

_HIDDEN_PROMPTS = {"reviewer"}


def seed_prompt_templates(mongo_uri: Optional[str] = None) -> int:
    """
    Insert the five prompt YAML files into prompt_templates collection if empty.

    Args:
        mongo_uri: MongoDB connection URI. Defaults to MONGO_URI env var.

    Returns:
        Number of documents inserted (0 if collection was already populated).
    """
    uri = mongo_uri or os.environ.get("MONGO_URI", "mongodb://localhost:27017/resume")
    client = MongoClient(uri)
    try:
        db_name = uri.rsplit("/", 1)[-1].split("?")[0] or "resume"
        collection = client[db_name]["prompt_templates"]

        if collection.count_documents({}) > 0:
            logger.info("prompt_templates already seeded — skipping")
            return 0

        now = datetime.now()
        docs = []
        for name in _YAML_NAMES:
            path = PROMPTS_DIR / f"{name}.yaml"
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            docs.append({
                "name": name,
                "description": _DESCRIPTIONS.get(name, ""),
                "version": 1,
                "messages": data["messages"],
                "create_time": now,
                "update_time": now,
                "delete_time": None,
                "is_delete": False,
                "is_show": name not in _HIDDEN_PROMPTS,
            })

        collection.insert_many(docs)
        logger.info("Seeded %d prompt templates", len(docs))
        return len(docs)
    finally:
        client.close()
