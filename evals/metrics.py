"""평가 메트릭 순수 함수"""

from __future__ import annotations

from lean_canvas.evaluation.models import HumanAgreementResult, Verdict

# 인간 평가 일치도 목표치
HUMAN_MAE_MAX = 0.5
HUMAN_WITHIN_ONE_MIN_RATIO = 0.8
HUMAN_BIAS_MAX = 0.3

# 판정 정확도 목표치
VERDICT_ACCURACY_MIN = 0.85
KAPPA_MIN = 0.6


def human_agreement(pairs: list[tuple[float, int]]) -> HumanAgreementResult:
    """(judge 점수, 사람 점수) 쌍 목록으로 MAE ±1 비율/평균오차를 계산한다.

    MAE는 절댓값이라 후함/박함의 쏠림을 못 보므로, 부호 있는 평균오차로 설정
    (signed_bias)로 방향성 치우침을 따로 측정, 쌍이 없으면 전부 미통과
    """
    if not pairs:
        return HumanAgreementResult(
            mae=0.0, within_one_ratio=0.0, signed_bias=0.0, n_compared=0,
            mae_pass=False, within_one_pass=False, bias_pass=False,
        )

    diffs = [judge - human for judge, human in pairs]
    mae = sum(abs(d) for d in diffs) / len(diffs)
    within_one_ratio = sum(1 for d in diffs if abs(d) <= 1.0) / len(diffs)
    signed_bias = sum(diffs) / len(diffs)

    return HumanAgreementResult(
        mae=mae,
        within_one_ratio=within_one_ratio,
        signed_bias=signed_bias,
        n_compared=len(pairs),
        mae_pass=mae <= HUMAN_MAE_MAX,
        within_one_pass=within_one_ratio >= HUMAN_WITHIN_ONE_MIN_RATIO,
        bias_pass=abs(signed_bias) <= HUMAN_BIAS_MAX,
    )


def verdict_accuracy(expected: list[Verdict], predicted: list[Verdict]) -> float:
    """범주 라벨과 시스템 판정의 단순 일치율"""
    if len(expected) != len(predicted):
        raise ValueError("expected와 predicted의 길이가 다릅니다.")
    if not expected:
        return 0.0
    matches = sum(1 for e, p in zip(expected, predicted) if e is p)
    return matches / len(expected)


def cohen_kappa(expected: list[Verdict], predicted: list[Verdict]) -> float:
    """우연 일치를 보정한 Cohen's Kappa"""
    if len(expected) != len(predicted):
        raise ValueError("expected와 predicted의 길이가 다릅니다.")
    if not expected:
        return 0.0

    n = len(expected)
    p_observed = sum(1 for e, p in zip(expected, predicted) if e is p) / n

    p_expected = 0.0
    for verdict in Verdict:
        p_expected += (
            (sum(1 for e in expected if e is verdict) / n)
            * (sum(1 for p in predicted if p is verdict) / n)
        )

    if p_expected == 1.0:
        return 1.0 if p_observed == 1.0 else 0.0
    return (p_observed - p_expected) / (1.0 - p_expected)
