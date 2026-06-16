"""CanvasJudge Facade 테스트(채점,재시도,집계 연결)"""

from __future__ import annotations

import pytest

from lean_canvas.evaluation.judge import CanvasJudge
from lean_canvas.evaluation.models import Verdict
from lean_canvas.llm.base import LLMError

from helpers import ScriptedLLMClient, make_judge_response


def test_evaluate_returns_aggregated_evaluation(fake_canvas):
    client = ScriptedLLMClient([make_judge_response(score=4)])
    evaluation = CanvasJudge(llm_client=client).evaluate(fake_canvas)

    assert evaluation.interest == fake_canvas.interest
    assert evaluation.canvas_score == pytest.approx(4.0)
    assert evaluation.verdict is Verdict.STRONG
    assert len(client.calls) == 1


def test_score_once_retries_on_malformed_response(fake_canvas):
    """1차 응답이 스키마 위반이면 위반 내용을 덧붙여 재시도하는지 확인"""
    bad = make_judge_response()
    del bad["problem"]["evidence"]
    client = ScriptedLLMClient([bad, make_judge_response(score=3)])

    scores = CanvasJudge(llm_client=client).score_once(fake_canvas)

    assert scores["problem"].evidence == 3
    assert len(client.calls) == 2
    # 재시도 프롬프트에 self-correction 피드백 포함
    retry_user_prompt = client.calls[1][1]["content"]
    assert "스키마를 위반했습니다" in retry_user_prompt
    assert "evidence" in retry_user_prompt


def test_score_once_fails_after_max_retries(fake_canvas):
    bad = make_judge_response()
    del bad["problem"]["evidence"]
    client = ScriptedLLMClient([dict(bad), dict(bad), dict(bad)])

    with pytest.raises(LLMError, match="3회 실패"):
        CanvasJudge(llm_client=client, max_retries=2).score_once(fake_canvas)
