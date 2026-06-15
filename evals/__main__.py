"""
평가 진입점 — python -m evals <command>

예시:
  python -m evals generate-canvases                 # 캐시 채우기 + 채점용 문서
  python -m evals run-judge-reliability --n 5       # 신뢰도
  python -m evals run-verdict-accuracy              # 판정 정확도 (저비용)
  python -m evals run-bias --limit 10               # 편향
  python -m evals run-pairwise --model-a gpt-4o-mini --model-b gpt-4o # pairwise 비교
  python -m evals list-results                      # 누적 런 요약
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from evals.config import EvalConfig
from evals.reporting import list_results


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset", type=Path, default=None, help="데이터셋 YAML 경로"
    )
    parser.add_argument(
        "--judge-model", default=None, help="judge 모델 (기본: JUDGE_MODEL env)"
    )
    parser.add_argument(
        "--gen-model", default=None, help="생성 모델 (기본: OPENAI_MODEL env)"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="데이터셋 앞에서 N개만 사용 (스모크용)"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="캔버스 생성 캐시 비활성화"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m evals",
        description="린 캔버스 측정 체계 실험 러너 (test.md 6장)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("generate-canvases", help="캔버스 일괄 생성 + 채점용 문서")
    _add_common_args(p)

    p = sub.add_parser("run-judge-reliability", help="실험 4 — judge 신뢰도")
    _add_common_args(p)
    p.add_argument("--n", type=int, default=5, help="self-consistency 채점 횟수")

    p = sub.add_parser("run-verdict-accuracy", help="판정 정확도 (항목당 1회)")
    _add_common_args(p)

    p = sub.add_parser("run-bias", help="실험 5 — judge 편향")
    _add_common_args(p)

    p = sub.add_parser("run-pairwise", help="pairwise A/B — 두 생성 모델 비교")
    _add_common_args(p)
    p.add_argument("--model-a", required=True, help="비교할 생성 모델 A")
    p.add_argument("--model-b", required=True, help="비교할 생성 모델 B")

    sub.add_parser("list-results", help="누적 실험 결과 요약")

    return parser.parse_args()


def _build_config(args: argparse.Namespace) -> EvalConfig:
    config = EvalConfig()
    if getattr(args, "dataset", None):
        config.dataset_path = args.dataset
    config.judge_model = getattr(args, "judge_model", None)
    config.gen_model = getattr(args, "gen_model", None)
    config.limit = getattr(args, "limit", None)
    config.use_cache = not getattr(args, "no_cache", False)
    if getattr(args, "n", None):
        config.n_runs = args.n
    return config


def main() -> None:
    load_dotenv()
    args = parse_args()

    if args.command == "list-results":
        summaries = list_results(EvalConfig().results_root)
        if not summaries:
            print("저장된 실험 결과가 없습니다.")
            return
        for s in summaries:
            print(f"{s['run']}: {s['title']} — 목표 통과 {s['passed']}/{s['total']}")
        return

    config = _build_config(args)

    # 실험 모듈은 openai 의존이 있으므로 명령 분기 후에 지연 import 한다.
    if args.command == "generate-canvases":
        from evals.experiments.generate import generate_canvases

        out_path = generate_canvases(config)
        print(f"\n채점용 문서 생성 완료: {out_path}")
    elif args.command == "run-judge-reliability":
        from evals.experiments.reliability import run_reliability

        run_dir = run_reliability(config)
        print(f"\n실험 완료. 결과: {run_dir}\\report.md")
    elif args.command == "run-verdict-accuracy":
        from evals.experiments.reliability import run_verdict_accuracy

        run_dir = run_verdict_accuracy(config)
        print(f"\n실험 완료. 결과: {run_dir}\\report.md")
    elif args.command == "run-bias":
        from evals.experiments.bias import run_bias

        run_dir = run_bias(config)
        print(f"\n실험 완료. 결과: {run_dir}\\report.md")
    elif args.command == "run-pairwise":
        from evals.experiments.pairwise_ab import run_pairwise_ab

        run_dir = run_pairwise_ab(config, model_a=args.model_a, model_b=args.model_b)
        print(f"\n실험 완료. 결과: {run_dir}\\report.md")


if __name__ == "__main__":
    main()
