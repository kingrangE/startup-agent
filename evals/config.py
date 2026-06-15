"""평가 실험 공통 설정"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalConfig:
    """실험 러너 공통 설정"""

    dataset_path: Path = Path("evals/data/eval_dataset.yaml")
    results_root: Path = Path("evals/results")
    n_runs: int = 5                  # self-consistency 채점 횟수
    judge_model: str | None = None   # None이면 JUDGE_MODEL 환경변수 (기본 gpt-4o)
    gen_model: str | None = None     # None이면 OPENAI_MODEL 환경변수 (기본 gpt-4o-mini)
    use_cache: bool = True           # 캔버스 생성 캐시 사용 여부
    limit: int | None = None         # 데이터셋 앞에서 N개만 사용 (smoke test용)

    @property
    def resolved_judge_model(self) -> str:
        return self.judge_model or os.getenv("JUDGE_MODEL", "gpt-4o")

    @property
    def resolved_gen_model(self) -> str:
        return self.gen_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def to_dict(self) -> dict:
        """config.json 저장용 직렬화"""
        return {
            "dataset_path": str(self.dataset_path),
            "results_root": str(self.results_root),
            "n_runs": self.n_runs,
            "judge_model": self.resolved_judge_model,
            "gen_model": self.resolved_gen_model,
            "use_cache": self.use_cache,
            "limit": self.limit,
        }
