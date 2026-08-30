from __future__ import annotations

from separk.benchmarks.hallucination import load_cases, run_benchmark


def test_twenty_case_benchmark_reaches_targets():
    cases = load_cases()
    assert len(cases) == 20
    assert len({case.id for case in cases}) == 20

    summary = run_benchmark(cases)

    assert summary.initial_hallucinations == 20
    assert summary.final_hallucinations == 0
    assert summary.final_hallucination_rate == 0.0
    assert summary.hallucination_target_passed
    assert summary.latency_overhead_percent < 10.0
    assert summary.latency_target_passed
