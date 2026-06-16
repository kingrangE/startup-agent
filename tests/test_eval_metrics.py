"""evals 메트릭 순수 함수 검증 — 인간 일치도 / 판정 정확도 / Cohen's κ / 편향 변형"""

from __future__ import annotations

import pytest

from evals.experiments.bias import inject_fake_evidence
from evals.metrics import cohen_kappa, human_agreement, verdict_accuracy
from lean_canvas.evaluation.models import Verdict


class TestHumanAgreement:
    def test_perfect_agreement(self):
        result = human_agreement([(4.0, 4), (3.0, 3), (5.0, 5)])
        assert result.mae == pytest.approx(0.0)
        assert result.within_one_ratio == pytest.approx(1.0)
        assert result.signed_bias == pytest.approx(0.0)
        assert result.mae_pass and result.within_one_pass and result.bias_pass

    def test_systematic_generosity_caught_by_signed_bias(self):
        """judge가 일관되게 0.6점 후하면 MAE는 0.6, 편향도 +0.6 — 둘 다 미통과"""
        result = human_agreement([(4.6, 4), (3.6, 3), (2.6, 2)])
        assert result.mae == pytest.approx(0.6)
        assert result.signed_bias == pytest.approx(+0.6)
        assert not result.mae_pass
        assert not result.bias_pass
        assert result.within_one_pass  # ±1 이내이긴 함

    def test_cancelling_errors_visible_only_in_mae(self):
        """+1/−1이 상쇄되면 편향은 0이지만 MAE는 1.0 — 두 지표가 보완 구조인지 확인"""
        result = human_agreement([(5.0, 4), (3.0, 4)])
        assert result.signed_bias == pytest.approx(0.0)
        assert result.mae == pytest.approx(1.0)

    def test_empty_pairs_fail_all(self):
        """결과가 빈 경우 비교 불가"""
        result = human_agreement([])
        assert result.n_compared == 0
        assert not (result.mae_pass or result.within_one_pass or result.bias_pass)


class TestVerdictMetrics:
    def test_accuracy(self):
        expected = [Verdict.STRONG, Verdict.NEEDS_WORK, Verdict.ACCEPTABLE]
        predicted = [Verdict.STRONG, Verdict.NEEDS_WORK, Verdict.STRONG]
        assert verdict_accuracy(expected, predicted) == pytest.approx(2 / 3)

    def test_kappa_perfect_agreement_is_one(self):
        labels = [Verdict.STRONG, Verdict.ACCEPTABLE, Verdict.NEEDS_WORK] * 3
        assert cohen_kappa(labels, list(labels)) == pytest.approx(1.0)

    def test_kappa_corrects_for_chance(self):
        """한쪽이 전부 같은 판정이면 일치율이 높아도 κ는 0 — 우연 보정."""
        expected = [Verdict.STRONG] * 8 + [Verdict.NEEDS_WORK] * 2
        predicted = [Verdict.STRONG] * 10
        assert verdict_accuracy(expected, predicted) == pytest.approx(0.8)
        assert cohen_kappa(expected, predicted) == pytest.approx(0.0)

    def test_length_mismatch_rejected(self):
        with pytest.raises(ValueError):
            cohen_kappa([Verdict.STRONG], [])


class TestFakeEvidenceInjection:
    """편향 실험용 변형 함수 — 순수/결정적이어야 한다."""

    def test_injects_citations_into_every_statement(self, fake_canvas):
        tampered = inject_fake_evidence(fake_canvas)
        for value in tampered.blocks().values():
            statements = value if isinstance(value, list) else [value]
            for statement in statements:
                assert "출처" in statement or "검증" in statement or "통계" in statement or "실증" in statement

    def test_preserves_original_content(self, fake_canvas):
        """실질 내용은 그대로 — 원문이 변형문 안에 포함"""
        tampered = inject_fake_evidence(fake_canvas)
        assert fake_canvas.problem[0] in tampered.problem[0]
        assert fake_canvas.unique_value_proposition in tampered.unique_value_proposition
        assert tampered.interest == fake_canvas.interest

    def test_deterministic(self, fake_canvas):
        assert inject_fake_evidence(fake_canvas) == inject_fake_evidence(fake_canvas)
