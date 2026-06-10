"""점수 집계 — 칸 점수·캔버스 총점·판정 매핑"""
from __future__ import annotations

from lean_canvas.evaluation.models import (
    BlockScore,
    CanvasEvaluation,
    JudgeScore,
    Verdict,
)
from lean_canvas.evaluation.rubric import (
    MIN_GUARD_CAP,
    MIN_GUARD_THRESHOLD,
    VERDICT_THRESHOLDS,
    WEIGHTS,
)


def block_score(scores: JudgeScore) -> float:
    """칸 점수 = 4개 항목의 가중 평균"""
    values = scores.as_dict()
    return sum(values[k] * w for k, w in WEIGHTS.items())


def canvas_score(block_scores: list[float]) -> tuple[float, bool]:
    """
    캔버스 총점 = 9칸 평균 + 과락

    어느 한 칸이라도 MIN_GUARD_THRESHOLD(2.0) 미만이면 총점 상한을 MIN_GUARD_CAP(3.0)으로 제한

    Args :
        block_scores: 각 칸 점수 리스트
    Returns:
        (총점, 가드 발동 여부)
    """
    if not block_scores:
        raise ValueError("칸 점수가 비어 있습니다.")
    avg = sum(block_scores) / len(block_scores)
    if min(block_scores) < MIN_GUARD_THRESHOLD:  # 최소 값이 임계보다 낮으면
        return min(avg, MIN_GUARD_CAP), True     # 총점 상한을 설정
    return avg, False


def map_verdict(score: float) -> Verdict:
    """
    canvas_score -> overall_verdict 범주 매핑
    """
    if score >= VERDICT_THRESHOLDS["strong"]:
        return Verdict.STRONG
    if score >= VERDICT_THRESHOLDS["acceptable"]:
        return Verdict.ACCEPTABLE
    return Verdict.NEEDS_WORK


def build_canvas_evaluation(
    interest: str,
    raw_scores: dict[str, JudgeScore],
) -> CanvasEvaluation:
    """블록별 원점수로 평가 결과 객체 완성"""
    blocks = tuple( # 각 블록 점수 모음
        BlockScore(block_key=key, raw=score, weighted=block_score(score))
        for key, score in raw_scores.items()
    )
    weighted_scores = [b.weighted for b in blocks] # 가중치를 반영한 점수 모음
    total, guard = canvas_score(weighted_scores) # 캔버스 총점 확인
    return CanvasEvaluation( # 결과 객체 반환
        interest=interest,
        blocks=blocks,
        canvas_score=total,
        min_block_score=min(weighted_scores),
        guard_triggered=guard,
        verdict=map_verdict(total),
    )
