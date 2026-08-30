"""Twenty-case offline hallucination and validator-latency benchmark."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path
from time import perf_counter

import yaml

from lean_canvas.models import LeanCanvas
from separk.agent.models import GroundedClaim, ResearchDraft, SearchResult
from separk.agent.validator import EvidenceValidator, sanitize_draft


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    interest: str
    evidence: str
    supported_claim: str
    hallucinated_claim: str
    baseline_latency_ms: float


@dataclass(frozen=True)
class BenchmarkSummary:
    case_count: int
    initial_hallucinations: int
    final_hallucinations: int
    final_hallucination_rate: float
    baseline_latency_ms: float
    validated_latency_ms: float
    latency_overhead_percent: float
    hallucination_target_passed: bool
    latency_target_passed: bool


def default_dataset_path() -> Path:
    return Path(
        str(files("separk").joinpath("benchmarks/data/hallucination_cases.yaml"))
    )


def load_cases(path: Path | None = None) -> tuple[BenchmarkCase, ...]:
    payload = yaml.safe_load(
        (path or default_dataset_path()).read_text(encoding="utf-8")
    )
    rows = payload.get("cases", []) if isinstance(payload, dict) else []
    cases = tuple(BenchmarkCase(**row) for row in rows)
    if len(cases) != 20:
        raise ValueError(f"환각 벤치마크는 정확히 20개여야 합니다: {len(cases)}개")
    return cases


def _draft(case: BenchmarkCase) -> tuple[ResearchDraft, tuple[SearchResult, ...]]:
    source = SearchResult(
        provider="benchmark",
        title=case.supported_claim,
        url=f"https://benchmark.invalid/{case.id}",
        snippet=case.evidence,
        source_id="S1",
    )
    canvas = LeanCanvas(
        interest=case.interest,
        problem=[case.supported_claim, case.hallucinated_claim],
    )
    draft = ResearchDraft(
        canvas=canvas,
        claims=(
            GroundedClaim("problem", case.supported_claim, "fact", ("S1",)),
            GroundedClaim("problem", case.hallucinated_claim, "fact", ("S1",)),
        ),
    )
    return draft, (source,)


def run_benchmark(
    cases: tuple[BenchmarkCase, ...] | None = None,
    validator: EvidenceValidator | None = None,
) -> BenchmarkSummary:
    selected = cases or load_cases()
    checker = validator or EvidenceValidator(min_token_overlap=0.3)
    initial_hallucinations = 0
    final_hallucinations = 0
    validator_elapsed_ms = 0.0

    for case in selected:
        draft, sources = _draft(case)
        started = perf_counter()
        initial = checker.validate(draft, sources)
        sanitized = sanitize_draft(draft, initial)
        final = checker.validate(sanitized, sources)
        validator_elapsed_ms += (perf_counter() - started) * 1000
        initial_hallucinations += int(case.hallucinated_claim in draft.canvas.problem)
        final_hallucinations += int(case.hallucinated_claim in sanitized.canvas.problem)
        if not final.valid:
            raise AssertionError(f"{case.id} 최종 검증 실패: {final.issues}")

    baseline_ms = sum(case.baseline_latency_ms for case in selected)
    validated_ms = baseline_ms + validator_elapsed_ms
    overhead = (
        ((validated_ms - baseline_ms) / baseline_ms * 100) if baseline_ms else 0.0
    )
    rate = final_hallucinations / len(selected) if selected else 0.0
    return BenchmarkSummary(
        case_count=len(selected),
        initial_hallucinations=initial_hallucinations,
        final_hallucinations=final_hallucinations,
        final_hallucination_rate=rate,
        baseline_latency_ms=baseline_ms,
        validated_latency_ms=validated_ms,
        latency_overhead_percent=overhead,
        hallucination_target_passed=rate == 0.0,
        latency_target_passed=overhead < 10.0,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="20개 환각·validator 지연 오프라인 벤치마크"
    )
    parser.add_argument("--dataset", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("benchmark-results/hallucination.json")
    )
    args = parser.parse_args(argv)
    summary = run_benchmark(load_cases(args.dataset))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return (
        0
        if summary.hallucination_target_passed and summary.latency_target_passed
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
