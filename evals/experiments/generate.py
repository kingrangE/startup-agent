"""
캔버스 일괄 생성 (캐시 채우기 + 사람 채점용 문서 출력)

human_scores 라벨은 이 아이디어로 생성된 캔버스에 매기는 점수
따라서 사람이 채점할 캔버스 전체를 하나의 Markdown으로 모으기
"""

from __future__ import annotations

from pathlib import Path

from evals.cache import CanvasCache
from evals.config import EvalConfig
from evals.dataset import load_dataset
from lean_canvas.factory import create_generator
from lean_canvas.renderers import MarkdownRenderer


def generate_canvases(config: EvalConfig) -> Path:
    """데이터셋 전체의 캔버스를 생성(캐시)하고 채점용 문서를 만든다."""
    items = load_dataset(config.dataset_path)
    if config.limit is not None:
        items = items[: config.limit]

    generator = create_generator(model=config.gen_model)
    cache = CanvasCache(
        config.results_root / "_canvas_cache", enabled=config.use_cache
    )
    renderer = MarkdownRenderer()

    lines = [
        "# 사람 채점용 생성 캔버스 모음",
        "",
        f"- 생성 모델: `{config.resolved_gen_model}`",
        "- 각 캔버스를 보고 evals/data/eval_dataset.yaml의 human_scores에",
        "  4차원(specificity·evidence·coherence·differentiation) 1~5점을 기입하세요.",
        "",
    ]
    for index, item in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] {item.id}: 캔버스 확보...")
        canvas = cache.get_or_generate(item, generator, config.resolved_gen_model)
        lines.append("---")
        lines.append("")
        lines.append(f"## {item.id} ({item.category} / 기대: {item.expected_verdict.value})")
        lines.append("")
        lines.append(renderer.render(canvas))
        lines.append("")

    out_path = Path(config.dataset_path).parent / "canvases_for_labeling.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
