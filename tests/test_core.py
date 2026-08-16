from pathlib import Path

import pytest

from code_assistant.core import answer, chunk_file, index_repo, load_index, retrieve, save_index

ROOT = Path(__file__).parent / "fixture"


def test_ast_chunking():
    chunks = chunk_file(ROOT / "sample.py", ROOT)
    assert {c.symbol for c in chunks} >= {"load_value", "normalize", "Service", "run"}


def test_dependency_graph_is_bidirectional():
    idx = index_repo(ROOT)
    load = next(c for c in idx["chunks"] if c["symbol"] == "load_value")
    normalize = next(c for c in idx["chunks"] if c["symbol"] == "normalize")
    assert normalize["id"] in idx["edges"][load["id"]]
    assert load["id"] in idx["reverse_edges"][normalize["id"]]


def test_retrieval_prioritizes_named_symbol():
    hits = retrieve(index_repo(ROOT), "where is normalize used?")
    assert hits[0]["symbol"] == "normalize"


def test_answer_contains_grounded_references():
    result = answer(index_repo(ROOT), "where is normalize used?")
    assert result["references"]
    assert "normalize" in result["answer"]
    assert result["suggested_diff"] is None


def test_index_round_trip(tmp_path):
    index = index_repo(ROOT)
    target = tmp_path / "index.json"
    save_index(index, target)
    assert load_index(target)["chunks"] == index["chunks"]


def test_missing_index_has_actionable_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Run the index command first"):
        load_index(tmp_path / "missing.json")


def test_empty_question_rejected():
    with pytest.raises(ValueError, match="Question cannot be empty"):
        answer(index_repo(ROOT), "   ")
