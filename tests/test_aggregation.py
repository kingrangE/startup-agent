"""집계 규칙 검증 — 가중 평균/min 가드/평가 조립"""

from __future__ import annotations

import pytest

from lean_canvas.evaluation.aggregation import (
    block_score,
    build_canvas_evaluation,
    canvas_score,
)
from lean_canvas.evaluation.models import JudgeScore, Verdict
from lean_canvas.evaluation.rubric import DIMENSIONS, MIN_GUARD_CAP, WEIGHTS
from lean_canvas.models import LeanCanvas

from helpers import make_judge_response
from lean_canvas.evaluation.parsing import parse_judge_response


def test_weights_sum_to_one():
    """가중치 합은 1.0, 키는 4차원과 정확히 일치"""
    assert sum(WEIGHTS.values()) == pytest.approx(1.0) # 총 합 검사
    assert set(WEIGHTS) == set(DIMENSIONS) # 구성 요소 일치 확인


def test_block_score_weighted_average():
    """칸 점수 = 4항목 가중합 (근거성 0.35 / 일관성 0.25 / 구체성 0.20 / 차별성 0.20)"""
    score = JudgeScore(specificity=4, evidence=5, coherence=3, differentiation=2)
    # 계산 잘하는지 검사, .35*4 + .25*5 + .2*3 + .2*2 == 3.7
    assert block_score(score) == pytest.approx(3.70)


def test_canvas_score_is_average_without_guard():
    """모든 칸이 2.0 이상이면 단순 평균 / 가드 X"""
    total, guard = canvas_score([4.0] * 9)
    assert total == pytest.approx(4.0)
    assert guard is False # 가드 발동 안 했나?


def test_min_guard_caps_average():
    """한 칸이라도 2.0 미만이면 총점 상한 3.0 / Guard On"""
    scores = [5.0] * 8 + [1.9]  # 평균 약 4.66
    total, guard = canvas_score(scores)
    assert total == pytest.approx(MIN_GUARD_CAP)
    assert guard is True # 가드 발동 했나?


def test_min_guard_boundary_exactly_two():
    """정확히 2.0인 칸은 가드 대상 X"""
    scores = [5.0] * 8 + [2.0]
    total, guard = canvas_score(scores)
    assert total == pytest.approx(sum(scores) / 9)
    assert guard is False # 가드 발동 안 한거 맞나?


def test_min_guard_keeps_average_when_already_below_cap():
    """가드가 발동해도 평균이 상한보다 낮으면 평균을 그대로 사용"""
    total, guard = canvas_score([1.5] * 9)
    assert total == pytest.approx(1.5)
    assert guard is True


def test_canvas_score_rejects_empty():
    with pytest.raises(ValueError):
        canvas_score([])


def test_build_canvas_evaluation_assembles_nine_blocks():
    """원점수 dict -> 9개 BlockScore + 총점 + 판정으로 조립"""
    raw_scores = parse_judge_response(make_judge_response(score=4)) # 모든 스코어 4 고정인 결과 생성 (원점수 dict) 
    evaluation = build_canvas_evaluation("반려동물 헬스케어", raw_scores)
    # 위 점수로 canvas 평가 진행 

    assert len(evaluation.blocks) == 9 # 개수가 맞는가
    assert [b.block_key for b in evaluation.blocks] == list(LeanCanvas.block_titles()) # 각 block 키 순서가 동일한가 
    assert evaluation.canvas_score == pytest.approx(4.0) # 모든 항목이 4.0이므로 평균이 4.0 맞나
    assert evaluation.guard_triggered is False # 과락 없으므로 트리거 X
    assert evaluation.verdict is Verdict.STRONG # 4니까 STRONG


def test_build_canvas_evaluation_guard_blocks_strong():
    """과락(<2)이 있으면 절대 strong이 될 수 없음"""
    response = make_judge_response(
        score=5,
        overrides={"problem": {dim: 1 for dim in DIMENSIONS}},
    )
    evaluation = build_canvas_evaluation(
        "테스트", parse_judge_response(response)
    )
    assert evaluation.guard_triggered is True
    assert evaluation.canvas_score <= 3.0
    assert evaluation.verdict is not Verdict.STRONG
