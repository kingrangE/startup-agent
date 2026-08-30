from __future__ import annotations

import pytest

from separk.agent.parsing import DraftParseError, parse_research_draft


def valid_payload() -> dict:
    return {
        "canvas": {
            "problem": ["검증된 문제"],
            "customer_segments": [],
            "unique_value_proposition": "",
            "solution": ["(가설) 해결책"],
            "channels": [],
            "revenue_streams": [],
            "cost_structure": [],
            "key_metrics": [],
            "unfair_advantage": "",
        },
        "claims": [
            {
                "block": "problem",
                "text": "검증된 문제",
                "kind": "fact",
                "source_ids": ["S1"],
            },
            {
                "block": "solution",
                "text": "(가설) 해결책",
                "kind": "hypothesis",
                "source_ids": [],
            },
        ],
    }


def test_parse_research_draft_preserves_claim_contract():
    draft = parse_research_draft("테스트", valid_payload())
    assert draft.canvas.problem == ["검증된 문제"]
    assert draft.claims[0].source_ids == ("S1",)
    assert draft.claims[1].kind == "hypothesis"


def test_parse_research_draft_rejects_missing_canvas_block():
    payload = valid_payload()
    del payload["canvas"]["channels"]
    with pytest.raises(DraftParseError, match="channels"):
        parse_research_draft("테스트", payload)


def test_parse_research_draft_rejects_unknown_claim_kind():
    payload = valid_payload()
    payload["claims"][0]["kind"] = "opinion"
    with pytest.raises(DraftParseError, match="fact 또는 hypothesis"):
        parse_research_draft("테스트", payload)
