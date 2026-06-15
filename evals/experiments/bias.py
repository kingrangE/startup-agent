"""
judge 편향 검증: 구체성,권위 편향 + 자기 선호 편향

절대 점수 방식 judge의 알려진 약점 두 가지를 능동적으로 측정
(1) 허위 출처,조작 수치를 삽입 시 점수가 오르는지
(2) 생성 AI와 동일한 backbone으로 채점하면 점수가 후한지
"""

from __future__ import annotations

from dataclasses import replace
from statistics import mean

from evals.cache import CanvasCache
from evals.config import EvalConfig
from evals.dataset import load_dataset
from evals.reporting import prepare_run_dir, save_raw, write_reports
from lean_canvas.factory import create_generator, create_judge
from lean_canvas.models import LeanCanvas

# 허위 단서 — 실존하지 않는 출처,조작 수치
FAKE_CITATIONS = (
    "(출처: 2025 가트너 산업 보고서, 시장 규모 12조 원)",
    "(스탠퍼드 연구진 실증, 효율 47% 개선 확인)",
    "(통계청 공식 통계, 연평균 성장률 23%)",
)

# 편향 점수 상승 허용 한도 — 이 이상 오르면 편향 의심
EVIDENCE_DELTA_MAX = 0.3


def inject_fake_evidence(canvas: LeanCanvas) -> LeanCanvas:
    """
    모든 진술에 허위 출처·조작 수치를 덧붙인 변형 캔버스 생성 순수 함수

    내용은 그대로 두고 표면적 권위 단서만 추가 
    judge가 사실 여부와 무관하게 evidence 점수를 올리면 구체성/권위 편향 존재
    """
    counter = 0

    def cite() -> str:
        # 출처 반환 함수
        nonlocal counter
        citation = FAKE_CITATIONS[counter % len(FAKE_CITATIONS)]
        counter += 1
        return citation

    def tamper_list(values: list[str]) -> list[str]:
        # 각 생성된 value에 대해 cite 추가 후 리스트 반환
        return [f"{v} {cite()}" for v in values]

    return replace(
        canvas,
        problem=tamper_list(canvas.problem),
        customer_segments=tamper_list(canvas.customer_segments),
        unique_value_proposition=f"{canvas.unique_value_proposition} {cite()}",
        solution=tamper_list(canvas.solution),
        channels=tamper_list(canvas.channels),
        revenue_streams=tamper_list(canvas.revenue_streams),
        cost_structure=tamper_list(canvas.cost_structure),
        key_metrics=tamper_list(canvas.key_metrics),
        unfair_advantage=f"{canvas.unfair_advantage} {cite()}",
    )


def run_bias(config: EvalConfig):
    """편향 2개 값 측정 — 항목당 채점 4회 (원본/변형 x 분리/동일 backbone 일부)"""
    items = load_dataset(config.dataset_path)
    if config.limit is not None:
        items = items[: config.limit]

    # 생성 LLM / 평가 LLM(모델 다른거) / 평가 LLM (모델 같은거)
    generator = create_generator(model=config.gen_model)
    separate_judge = create_judge(model=config.judge_model)       
    same_backbone_judge = create_judge(model=config.resolved_gen_model)

    # 캐시를 활용하여 테스트 과정에서 불필요하게 생성하지 않도록
    cache = CanvasCache(
        config.results_root / "_canvas_cache", enabled=config.use_cache
    )

    authority_rows = []   # 구체성/권위 편향: 원본 vs 허위 출처 변형
    self_pref_rows = []   # 자기 선호 편향: 분리 backbone vs 동일 backbone
    for index, item in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] {item.id}: 편향 측정 채점...")
        canvas = cache.get_or_generate(item, generator, config.resolved_gen_model)
        tampered = inject_fake_evidence(canvas)  # 변형본은 캐시하지 않는다

        original = separate_judge.evaluate(canvas)
        forged = separate_judge.evaluate(tampered)
        authority_rows.append(
            {
                "id": item.id,
                "original_score": original.canvas_score,
                "forged_score": forged.canvas_score,
                "original_evidence": original.dimension_means()["evidence"],
                "forged_evidence": forged.dimension_means()["evidence"],
            }
        )

        same_backbone = same_backbone_judge.evaluate(canvas)
        self_pref_rows.append(
            {
                "id": item.id,
                "separate_score": original.canvas_score,
                "same_backbone_score": same_backbone.canvas_score,
            }
        )

    evidence_delta = mean(
        r["forged_evidence"] - r["original_evidence"] for r in authority_rows
    )
    score_delta = mean(
        r["forged_score"] - r["original_score"] for r in authority_rows
    )
    self_pref_delta = mean(
        r["same_backbone_score"] - r["separate_score"] for r in self_pref_rows
    )

    payload = {
        "experiment": "judge-bias",
        "title": "judge 편향 검증 (허위 출처 주입·자기 선호)",
        "config": config.to_dict(),
        "metrics": [
            {
                "name": "허위 출처 주입 시 evidence 평균 변화",
                "value": f"{evidence_delta:+.3f}",
                "target": f"≤ +{EVIDENCE_DELTA_MAX}",
                "passed": evidence_delta <= EVIDENCE_DELTA_MAX,
            },
            {
                "name": "허위 출처 주입 시 총점 평균 변화",
                "value": f"{score_delta:+.3f}",
                "target": f"≤ +{EVIDENCE_DELTA_MAX}",
                "passed": score_delta <= EVIDENCE_DELTA_MAX,
            },
            {
                "name": "자기 선호 편향 (동일 backbone − 분리)",
                "value": f"{self_pref_delta:+.3f}",
                "target": "양수면 동일 backbone일 때 좋게 평가한다는 것",
                "passed": None,
            },
        ],
        "notes": [
            f"분리 backbone: {config.resolved_judge_model}, "
            f"동일 backbone: {config.resolved_gen_model}",
        ],
    }

    run_dir = prepare_run_dir(config, "judge-bias")
    save_raw(run_dir, {"authority": authority_rows, "self_preference": self_pref_rows})
    write_reports(run_dir, payload)
    return run_dir
