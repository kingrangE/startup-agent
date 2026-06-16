"""self-consistency계산 검증"""

from __future__ import annotations

from statistics import pstdev

import pytest

from lean_canvas.evaluation.judge import CanvasJudge
from lean_canvas.evaluation.rubric import DIMENSIONS

from helpers import ScriptedLLMClient, make_judge_response


def test_identical_runs_have_zero_std_and_pass(fake_canvas):
    """N회 점수가 완전히 같으면 통과"""
    client = ScriptedLLMClient([make_judge_response(score=4) for _ in range(5)])
    result = CanvasJudge(llm_client=client).self_consistency(fake_canvas, n=5)

    assert result.n_runs == 5
    assert result.canvas_score_std == pytest.approx(0.0)
    assert all(v == pytest.approx(0.0) for v in result.per_dimension_std.values())
    assert result.passed is True


def test_varying_runs_fail_threshold(fake_canvas):
    """점수가 크게 변화하면(>0.3) 불통"""
    client = ScriptedLLMClient(
        [make_judge_response(score=s) for s in (2, 5, 2, 5, 2)]
    )
    result = CanvasJudge(llm_client=client).self_consistency(fake_canvas, n=5)

    # 일괄 점수라 칸 점수 = canvas_score = 해당 run 점수
    assert result.canvas_scores == pytest.approx((2.0, 5.0, 2.0, 5.0, 2.0))
    assert result.canvas_score_std == pytest.approx(pstdev([2, 5, 2, 5, 2]))
    assert result.passed is False


def test_dimension_means_and_majority_verdict(fake_canvas):
    """차원별 평균과 다수결 판정이 N회 결과로부터 계산되는지 검증"""
    client = ScriptedLLMClient(
        [make_judge_response(score=s) for s in (4, 4, 3)]
    )
    result = CanvasJudge(llm_client=client).self_consistency(fake_canvas, n=3)

    means = result.dimension_means()
    for dim in DIMENSIONS:
        assert means[dim] == pytest.approx((4 + 4 + 3) / 3)
    # 4점 run 2회(strong), 3점 run 1회(acceptable) -> 다수결 strong
    assert result.majority_verdict().value == "strong"


def test_requires_at_least_two_runs(fake_canvas):
    client = ScriptedLLMClient([make_judge_response()])
    with pytest.raises(ValueError):
        CanvasJudge(llm_client=client).self_consistency(fake_canvas, n=1)
