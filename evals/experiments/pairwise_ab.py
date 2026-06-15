"""
pairwise A/B 비교 — 두 생성 모델의 캔버스 직접 비교

루프 전/후 비교는 루프 도입 후 사용하고, 생성 모델 A vs B의 개선 승률(win rate)과 위치 일관성을 측정
"""

from __future__ import annotations

from evals.cache import CanvasCache
from evals.config import EvalConfig
from evals.dataset import load_dataset
from evals.reporting import prepare_run_dir, save_raw, write_reports
from lean_canvas.factory import create_generator, create_pairwise_judge


def run_pairwise_ab(config: EvalConfig, model_a: str, model_b: str):
    """데이터셋의 각 아이디어를 두 모델로 생성해 pairwise로 비교"""
    items = load_dataset(config.dataset_path)
    if config.limit is not None:
        items = items[: config.limit]

    generator_a = create_generator(model=model_a)
    generator_b = create_generator(model=model_b)
    judge = create_pairwise_judge(model=config.judge_model)
    cache = CanvasCache(
        config.results_root / "_canvas_cache", enabled=config.use_cache
    )

    rows = []
    for index, item in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] {item.id}: 두 모델 생성 후 비교...")
        canvas_a = cache.get_or_generate(item, generator_a, model_a)
        canvas_b = cache.get_or_generate(item, generator_b, model_b)
        result = judge.compare(canvas_a, canvas_b)
        rows.append((item, result))

    total = len(rows)
    wins_a = sum(1 for _, r in rows if r.winner == "A")
    wins_b = sum(1 for _, r in rows if r.winner == "B")
    ties = sum(1 for _, r in rows if r.winner == "tie")
    position_consistency = sum(1 for _, r in rows if r.position_consistent) / total

    payload = {
        "experiment": "pairwise-ab",
        "title": f"pairwise A/B — {model_a} vs {model_b}",
        "config": {**config.to_dict(), "model_a": model_a, "model_b": model_b},
        "metrics": [
            {
                "name": f"A({model_a}) 승률",
                "value": f"{wins_a / total:.0%}",
                "target": "참고용",
                "passed": None,
            },
            {
                "name": f"B({model_b}) 승률",
                "value": f"{wins_b / total:.0%}",
                "target": "참고용",
                "passed": None,
            },
            {
                "name": "무승부 (위치 비일관 포함)",
                "value": f"{ties / total:.0%}",
                "target": "참고용",
                "passed": None,
            },
            {
                "name": "위치 일관성 (position consistency)",
                "value": f"{position_consistency:.0%}",
                "target": "높을수록 judge가 안정적",
                "passed": None,
            },
        ],
        "notes": [
            "정/역 순서로 2회 질의해 판정이 뒤집히면 무승부 처리한다 (test.md 6.6).",
            "루프 도입 후에는 같은 머신으로 루프 전/후 캔버스를 비교해 "
            "개선 승률(목표 70%)을 측정한다.",
        ],
    }

    raw = {
        "per_item": [
            {
                "id": item.id,
                "winner": r.winner,
                "first_pass": r.first_pass,
                "swapped_pass": r.swapped_pass,
                "position_consistent": r.position_consistent,
                "rationale": r.rationale,
            }
            for item, r in rows
        ]
    }

    run_dir = prepare_run_dir(config, "pairwise-ab")
    save_raw(run_dir, raw)
    write_reports(run_dir, payload)
    return run_dir
