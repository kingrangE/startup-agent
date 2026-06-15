"""
judge 신뢰도 검증(self-consistency,인간 일치도,판정 정확도)

1. "judge 점수를 왜 믿느냐"는 반박을 점수가 흔들리는지(σ)
2. 사람과 맞는지(MAE·±1·평균오차)
3. 최종 판정이 맞는지(정확도·κ·나쁜→strong 0건)로 확인
"""

from __future__ import annotations

from evals.cache import CanvasCache
from evals.config import EvalConfig
from evals.dataset import load_dataset
from evals.metrics import (
    HUMAN_BIAS_MAX,
    HUMAN_MAE_MAX,
    HUMAN_WITHIN_ONE_MIN_RATIO,
    KAPPA_MIN,
    VERDICT_ACCURACY_MIN,
    cohen_kappa,
    human_agreement,
    verdict_accuracy,
)
from evals.reporting import prepare_run_dir, save_raw, write_reports
from lean_canvas.evaluation.models import (
    EvalDatasetItem,
    SelfConsistencyResult,
    Verdict,
)
from lean_canvas.evaluation.rubric import DIMENSIONS, SELF_CONSISTENCY_MAX_STD
from lean_canvas.factory import create_generator, create_judge


def _load_items(config: EvalConfig) -> list[EvalDatasetItem]:
    items = load_dataset(config.dataset_path)
    if config.limit is not None:
        items = items[: config.limit]
    return items


def run_reliability(config: EvalConfig):
    """데이터셋 전체에 self-consistency(N회 채점) 수행 후 신뢰도 집계"""
    items = _load_items(config)
    generator = create_generator(model=config.gen_model)
    judge = create_judge(model=config.judge_model)
    cache = CanvasCache(
        config.results_root / "_canvas_cache", enabled=config.use_cache
    )

    per_item: list[tuple[EvalDatasetItem, SelfConsistencyResult]] = []
    for index, item in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] {item.id}: 캔버스 확보 후 {config.n_runs}회 채점...")
        canvas = cache.get_or_generate(item, generator, config.resolved_gen_model)
        result = judge.self_consistency(canvas, n=config.n_runs)
        per_item.append((item, result))

    # self-consistency — 항목별 σ의 최대/평균과 통과 비율
    score_stds = [sc.canvas_score_std for _, sc in per_item]
    consistency_pass_ratio = sum(1 for _, sc in per_item if sc.passed) / len(per_item)

    # 인간 일치도 — human_scores 라벨이 있는 항목만 비교
    pairs: list[tuple[float, int]] = []
    for item, sc in per_item:
        if item.human_scores:
            judge_means = sc.dimension_means()
            pairs.extend(
                (judge_means[dim], item.human_scores[dim]) for dim in DIMENSIONS
            )
    agreement = human_agreement(pairs)

    # 판정 정확도 — 다수결 판정 vs 기대 판정
    expected = [item.expected_verdict for item, _ in per_item]
    predicted = [sc.majority_verdict() for _, sc in per_item]
    accuracy = verdict_accuracy(expected, predicted)
    kappa = cohen_kappa(expected, predicted)
    bad_to_strong = sum(
        1
        for item, sc in per_item
        if item.category == "bad" and sc.majority_verdict() is Verdict.STRONG
    )

    payload = {
        "experiment": "judge-reliability",
        "title": "실험 4 — judge 신뢰도 검증 (self-consistency·인간 일치도·판정 정확도)",
        "config": config.to_dict(),
        "metrics": [
            {
                "name": "self-consistency σ (최대)",
                "value": f"{max(score_stds):.3f}",
                "target": f"≤ {SELF_CONSISTENCY_MAX_STD}",
                "passed": max(score_stds) <= SELF_CONSISTENCY_MAX_STD,
            },
            {
                "name": "self-consistency σ (평균)",
                "value": f"{sum(score_stds) / len(score_stds):.3f}",
                "target": f"≤ {SELF_CONSISTENCY_MAX_STD}",
                "passed": sum(score_stds) / len(score_stds)
                <= SELF_CONSISTENCY_MAX_STD,
            },
            {
                "name": "self-consistency 통과 항목 비율",
                "value": f"{consistency_pass_ratio:.0%}",
                "target": "참고용",
                "passed": None,
            },
            {
                "name": "MAE (judge vs 사람)",
                "value": f"{agreement.mae:.3f}" if agreement.n_compared else "라벨 없음",
                "target": f"≤ {HUMAN_MAE_MAX}",
                "passed": agreement.mae_pass if agreement.n_compared else None,
            },
            {
                "name": "±1점 이내 비율",
                "value": f"{agreement.within_one_ratio:.0%}"
                if agreement.n_compared
                else "라벨 없음",
                "target": f"≥ {HUMAN_WITHIN_ONE_MIN_RATIO:.0%}",
                "passed": agreement.within_one_pass if agreement.n_compared else None,
            },
            {
                "name": "평균오차 (bias, judge−사람)",
                "value": f"{agreement.signed_bias:+.3f}"
                if agreement.n_compared
                else "라벨 없음",
                "target": f"|편향| ≤ {HUMAN_BIAS_MAX}",
                "passed": agreement.bias_pass if agreement.n_compared else None,
            },
            {
                "name": "판정 정확도",
                "value": f"{accuracy:.0%}",
                "target": f"≥ {VERDICT_ACCURACY_MIN:.0%}",
                "passed": accuracy >= VERDICT_ACCURACY_MIN,
            },
            {
                "name": "Cohen's κ",
                "value": f"{kappa:.3f}",
                "target": f"≥ {KAPPA_MIN}",
                "passed": kappa >= KAPPA_MIN,
            },
            {
                "name": '"나쁜→strong" 오판',
                "value": f"{bad_to_strong}건",
                "target": "0건",
                "passed": bad_to_strong == 0,
            },
        ],
        "notes": [
            f"인간 일치도는 human_scores 라벨이 있는 항목만 비교 (쌍 {agreement.n_compared}개). "
            "라벨은 evals/data/eval_dataset.yaml에서 채점",
            "σ가 높으면 앵커 예시 보강 또는 temperature 하향, MAE·편향이 크면 "
            "rubric 재정의 또는 임계값 보정",
        ],
    }

    raw = {
        "per_item": [
            {
                "id": item.id,
                "category": item.category,
                "expected_verdict": item.expected_verdict.value,
                "majority_verdict": sc.majority_verdict().value,
                "canvas_scores": list(sc.canvas_scores),
                "canvas_score_std": sc.canvas_score_std,
                "per_dimension_std": sc.per_dimension_std,
                "dimension_means": sc.dimension_means(),
                "consistency_passed": sc.passed,
            }
            for item, sc in per_item
        ]
    }

    run_dir = prepare_run_dir(config, "judge-reliability")
    save_raw(run_dir, raw)
    write_reports(run_dir, payload)
    return run_dir


def run_verdict_accuracy(config: EvalConfig):
    """판정 정확도만 빠르게 측정 — 항목당 1회 채점 (저비용 버전)"""
    items = _load_items(config)
    generator = create_generator(model=config.gen_model)
    judge = create_judge(model=config.judge_model)
    cache = CanvasCache(
        config.results_root / "_canvas_cache", enabled=config.use_cache
    )

    rows = []
    for index, item in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] {item.id}: 채점...")
        canvas = cache.get_or_generate(item, generator, config.resolved_gen_model)
        evaluation = judge.evaluate(canvas)
        rows.append((item, evaluation))

    expected = [item.expected_verdict for item, _ in rows]
    predicted = [e.verdict for _, e in rows]
    accuracy = verdict_accuracy(expected, predicted)
    kappa = cohen_kappa(expected, predicted)
    bad_to_strong = sum(
        1
        for item, e in rows
        if item.category == "bad" and e.verdict is Verdict.STRONG
    )

    payload = {
        "experiment": "verdict-accuracy",
        "title": "판정 정확도 — overall_verdict vs 범주 라벨 (항목당 1회 채점)",
        "config": config.to_dict(),
        "metrics": [
            {
                "name": "판정 정확도",
                "value": f"{accuracy:.0%}",
                "target": f"≥ {VERDICT_ACCURACY_MIN:.0%}",
                "passed": accuracy >= VERDICT_ACCURACY_MIN,
            },
            {
                "name": "Cohen's κ",
                "value": f"{kappa:.3f}",
                "target": f"≥ {KAPPA_MIN}",
                "passed": kappa >= KAPPA_MIN,
            },
            {
                "name": '"나쁜→strong" 오판',
                "value": f"{bad_to_strong}건",
                "target": "0건",
                "passed": bad_to_strong == 0,
            },
        ],
        "notes": [
            "항목당 1회 채점이므로 점수 노이즈에 노출된다. 정식 수치는 "
            "run-judge-reliability(다수결 판정)를 사용할 것.",
        ],
    }

    raw = {
        "per_item": [
            {
                "id": item.id,
                "category": item.category,
                "expected_verdict": item.expected_verdict.value,
                "verdict": e.verdict.value,
                "canvas_score": e.canvas_score,
                "guard_triggered": e.guard_triggered,
            }
            for item, e in rows
        ]
    }

    run_dir = prepare_run_dir(config, "verdict-accuracy")
    save_raw(run_dir, raw)
    write_reports(run_dir, payload)
    return run_dir
