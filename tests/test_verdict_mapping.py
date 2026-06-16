"""canvas_score -> overall_verdict 매핑 경계 검증"""

from __future__ import annotations

from lean_canvas.evaluation.aggregation import map_verdict
from lean_canvas.evaluation.models import Verdict
from lean_canvas.evaluation.rubric import VERDICT_THRESHOLDS


def test_strong_boundary():
    """임계값(4.0) 이상이면 strong, 미만이면 아님"""
    threshold = VERDICT_THRESHOLDS["strong"]
    assert map_verdict(threshold) is Verdict.STRONG
    assert map_verdict(5.0) is Verdict.STRONG
    assert map_verdict(threshold - 0.001) is not Verdict.STRONG


def test_acceptable_boundary():
    """acceptable 임계값(2.8) 이상 ~ strong 미만 구간"""
    threshold = VERDICT_THRESHOLDS["acceptable"]
    assert map_verdict(threshold) is Verdict.ACCEPTABLE
    assert map_verdict(3.5) is Verdict.ACCEPTABLE
    assert map_verdict(threshold - 0.001) is Verdict.NEEDS_WORK


def test_needs_work_floor():
    assert map_verdict(1.0) is Verdict.NEEDS_WORK
