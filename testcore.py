import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from pydantic import ValidationError
from core.ingest import chunk_text, clean_text
from core.llm import extract_json
from core.models import Question, GradeResult
from core.grade import check_objective


def test_chunking_by_headings():
    cs = chunk_text("1.1 Motion\nA body moves.\n1.2 Force\nA push or pull.")
    assert [c.ref for c in cs] == ["1.1 Motion", "1.2 Force"]


def test_clean_removes_page_numbers():
    assert "12" not in clean_text("Hello world.\n12\nPage 13\nBye.").split("\n")


def test_json_extraction_and_validation():
    raw = 'Sure!\n```json\n{"score": 2, "feedback": "ok"}\n```'
    assert GradeResult.model_validate_json(extract_json(raw)).score == 2
    with pytest.raises(ValueError):
        extract_json("no json here")


def _mcq(**k):
    d = dict(qtype="mcq", question="Q?", options=["a", "b", "c", "d"], answer="b")
    return Question(**{**d, **k})


def test_mcq_validation():
    with pytest.raises(ValidationError):
        _mcq(options=["a", "b", "c"])
    assert _mcq(answer="b").answer == "B"


def test_mcq_checking():
    q = _mcq()
    assert check_objective(q, 1) and not check_objective(q, 0) and not check_objective(q, None)


def test_fill_and_tf():
    f = Question(qtype="fill", question="__", answer="velocity|speed")
    assert check_objective(f, " Speed. ") and not check_objective(f, "mass")
    assert check_objective(Question(qtype="tf", question="x", answer="true"), "True")
