import pytest
from unittest.mock import MagicMock, patch
from llm.seed_prompts import seed_prompt_templates

YAML_NAMES = ["section_highlighter", "skills_matcher", "summary_writer", "improver", "reviewer"]


def _make_mock_collection(count=0):
    """Return a mock pymongo collection where count_documents returns `count`."""
    col = MagicMock()
    col.count_documents.return_value = count
    col.insert_many.return_value = MagicMock(inserted_ids=[MagicMock()] * 5)
    return col


def _make_mock_client(collection):
    client = MagicMock()
    client.__getitem__.return_value.__getitem__.return_value = collection
    return client


@patch("llm.seed_prompts.MongoClient")
def test_seed_inserts_five_docs_when_collection_empty(mock_client_cls):
    col = _make_mock_collection(count=0)
    mock_client_cls.return_value = _make_mock_client(col)

    count = seed_prompt_templates("mongodb://localhost/test")

    assert count == 5
    col.insert_many.assert_called_once()
    inserted = col.insert_many.call_args[0][0]
    names = [doc["name"] for doc in inserted]
    for name in YAML_NAMES:
        assert name in names


@patch("llm.seed_prompts.MongoClient")
def test_seed_skips_when_collection_not_empty(mock_client_cls):
    col = _make_mock_collection(count=4)
    mock_client_cls.return_value = _make_mock_client(col)

    count = seed_prompt_templates("mongodb://localhost/test")

    assert count == 0
    col.insert_many.assert_not_called()


@patch("llm.seed_prompts.MongoClient")
def test_seed_documents_have_required_fields(mock_client_cls):
    col = _make_mock_collection(count=0)
    mock_client_cls.return_value = _make_mock_client(col)

    seed_prompt_templates("mongodb://localhost/test")

    inserted = col.insert_many.call_args[0][0]
    for doc in inserted:
        assert "name" in doc
        assert "messages" in doc
        assert "version" in doc
        assert doc["version"] == 1
        assert "description" in doc
        assert isinstance(doc["messages"], list)
        assert len(doc["messages"]) > 0


@patch("llm.seed_prompts.MongoClient")
def test_seed_uses_env_mongo_uri_as_default(mock_client_cls, monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://envhost/mydb")
    col = _make_mock_collection(count=0)
    mock_client_cls.return_value = _make_mock_client(col)

    seed_prompt_templates()  # no explicit uri

    mock_client_cls.assert_called_once_with("mongodb://envhost/mydb")


@patch("llm.seed_prompts.MongoClient")
def test_seed_includes_reviewer_with_is_show_false(mock_client_cls):
    col = _make_mock_collection(count=0)
    mock_client_cls.return_value = _make_mock_client(col)

    seed_prompt_templates("mongodb://localhost/test")

    inserted = col.insert_many.call_args[0][0]
    reviewer_docs = [doc for doc in inserted if doc["name"] == "reviewer"]
    assert len(reviewer_docs) == 1
    assert reviewer_docs[0]["is_show"] is False

    reviewer_doc = next(d for d in inserted if d["name"] == "reviewer")
    non_reviewer_doc = next(d for d in inserted if d["name"] == "section_highlighter")
    assert reviewer_doc["is_show"] is False
    assert non_reviewer_doc["is_show"] is True
