"""pairwise 비교 검증 — 정/역 2회 질의와 위치 일관성 처리"""

from __future__ import annotations

import pytest

from lean_canvas.evaluation.pairwise import PairwiseJudge
from lean_canvas.llm.base import LLMError
from lean_canvas.models import LeanCanvas

from helpers import ScriptedLLMClient


@pytest.fixture
def canvas_a() -> LeanCanvas:
    return LeanCanvas(interest="아이디어 A", problem=["A의 문제"])


@pytest.fixture
def canvas_b() -> LeanCanvas:
    return LeanCanvas(interest="아이디어 B", problem=["B의 문제"])


def test_consistent_judgments_yield_winner(canvas_a, canvas_b):
    """원순서에서 답안A 승, 교체 순서에서 답안A 승 -> A가 최종 승리되는지 검증"""
    client = ScriptedLLMClient([
        {"winner": "1", "rationale": "A가 구체적"},
        {"winner": "2", "rationale": "A가 구체적"},
    ])
    result = PairwiseJudge(llm_client=client).compare(canvas_a, canvas_b)

    assert result.winner == "A"
    assert result.first_pass == "A"
    assert result.swapped_pass == "A"
    assert result.position_consistent is True
    assert len(client.calls) == 2  # 반드시 2회 질의


def test_position_flip_yields_tie(canvas_a, canvas_b):
    """두 번 모두 앞 답안을 고르면, 무승부 처리"""
    client = ScriptedLLMClient([
        {"winner": "1", "rationale": "앞이 좋아 보임"},
        {"winner": "1", "rationale": "앞이 좋아 보임"},
    ])
    result = PairwiseJudge(llm_client=client).compare(canvas_a, canvas_b)

    assert result.winner == "tie"
    assert result.first_pass == "A"
    assert result.swapped_pass == "B"
    assert result.position_consistent is False


def test_presentation_order_is_swapped_between_calls(canvas_a, canvas_b):
    """2차 질의에서는 제시 순서가 변경 되는지 검증"""
    client = ScriptedLLMClient([
        {"winner": "1"},
        {"winner": "2"},
    ])
    PairwiseJudge(llm_client=client).compare(canvas_a, canvas_b)

    first_user = client.calls[0][1]["content"]
    swapped_user = client.calls[1][1]["content"]
    assert first_user.index("아이디어 A") < first_user.index("아이디어 B")
    assert swapped_user.index("아이디어 B") < swapped_user.index("아이디어 A")


def test_invalid_winner_retried_then_fails(canvas_a, canvas_b):
    """winner가 1/2가 아니면 재시도, 전부 실패 시 LLMError"""
    client = ScriptedLLMClient([
        {"winner": "draw"},
        {"winner": "1"},   # 1차 질의의 재시도 성공
        {"winner": "2"},   # 2차(교체) 질의
    ])
    result = PairwiseJudge(llm_client=client).compare(canvas_a, canvas_b)
    assert result.winner == "A"

    failing = ScriptedLLMClient([{"winner": "draw"}] * 3)
    with pytest.raises(LLMError):
        PairwiseJudge(llm_client=failing, max_retries=2).compare(canvas_a, canvas_b)
