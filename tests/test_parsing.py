"""
Unit tests for the AI output parser. No network required.

Run with:  python -m pytest tests/test_parsing.py
"""
from app.tree_ai import _parse_ranking

VALID = ["22", "23", "26"]


def test_clean_json():
    out = _parse_ranking('{"ranked":["26","23"],"confidence":"high","clarify_questions":[]}', VALID)
    assert out == {"ranked": ["26", "23"], "confidence": "high", "clarify_questions": []}


def test_fenced_json():
    raw = '```json\n{"ranked":["26"],"confidence":"medium","clarify_questions":[]}\n```'
    out = _parse_ranking(raw, VALID)
    assert out["ranked"] == ["26"]
    assert out["confidence"] == "medium"


def test_invalid_codes_dropped():
    out = _parse_ranking('{"ranked":["99","22"],"confidence":"high"}', VALID)
    assert out["ranked"] == ["22"]


def test_bad_confidence_normalized():
    out = _parse_ranking('{"ranked":["22"],"confidence":"super-sure"}', VALID)
    assert out["confidence"] == "medium"


def test_plain_text_fallback():
    out = _parse_ranking("26 - Electrical", VALID)
    assert out["ranked"] == ["26"]
    assert out["confidence"] == "low"


def test_garbage_returns_empty():
    out = _parse_ranking("I cannot help with that", VALID)
    assert out["ranked"] == []


def test_clarify_questions_passthrough():
    raw = ('{"ranked":["22","23"],"confidence":"low",'
           '"clarify_questions":["Is the pump for plumbing or HVAC?","What size?"]}')
    out = _parse_ranking(raw, VALID)
    assert out["clarify_questions"] == ["Is the pump for plumbing or HVAC?", "What size?"]
    assert out["confidence"] == "low"


def test_legacy_single_clarify_coerced_to_list():
    raw = '{"ranked":["22"],"confidence":"low","clarify":"Plumbing or HVAC?"}'
    out = _parse_ranking(raw, VALID)
    assert out["clarify_questions"] == ["Plumbing or HVAC?"]
