from app.ai_gateway.json_cleaner import JSONCleanError, extract_json_text, loads_llm_json


def test_strips_markdown_fence() -> None:
    raw = '```json\n{"pace": "relaxed"}\n```'
    assert loads_llm_json(raw) == {"pace": "relaxed"}


def test_strips_surrounding_prose() -> None:
    raw = 'Sure, here you go:\n{"interests": ["food"]}\nHope that helps!'
    assert loads_llm_json(raw) == {"interests": ["food"]}


def test_fixes_trailing_commas() -> None:
    raw = '{"interests": ["food",], "hidden_gems": false,}'
    assert loads_llm_json(raw) == {"interests": ["food"], "hidden_gems": False}


def test_extracts_first_object_not_later_prose() -> None:
    raw = '{"a": 1} trailing {"a": 2}'
    assert loads_llm_json(raw) == {"a": 1}


def test_rejects_empty_output() -> None:
    try:
        extract_json_text("   ")
    except JSONCleanError:
        return
    raise AssertionError("expected JSONCleanError")


def test_does_not_invent_fields() -> None:
    parsed = loads_llm_json('{"pace": "moderate"}')
    assert parsed == {"pace": "moderate"}
    assert "interests" not in parsed
