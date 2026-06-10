"""평가 결과 도메인 모델 — LeanCanvas(models.py)와 동일한 frozen dataclass"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from lean_canvas.evaluation.rubric import DIMENSIONS


class Verdict(str, Enum):
    """캔버스 최종 판정 범주"""

    STRONG = "strong" # 좋음
    ACCEPTABLE = "acceptable" # 보통
    NEEDS_WORK = "needs_work" # 별로


# 판정 보수성 순서 — 동률일 때 더 보수적인 판정을 택하기 위한 기준
_VERDICT_ORDER = {Verdict.NEEDS_WORK: 0, Verdict.ACCEPTABLE: 1, Verdict.STRONG: 2}


@dataclass(frozen=True)
class JudgeScore:
    """한 블록에 대한 4기준 채점 결과"""

    specificity: int
    evidence: int
    coherence: int
    differentiation: int
    rationale: str = ""  # judge가 남긴 한두 문장의 채점 근거

    def as_dict(self) -> dict[str, int]:
        return {dim: getattr(self, dim) for dim in DIMENSIONS}


@dataclass(frozen=True)
class BlockScore:
    """블록 키 + 원점수 + 가중평균 점수"""

    block_key: str
    raw: JudgeScore
    weighted: float


@dataclass(frozen=True)
class CanvasEvaluation:
    """캔버스 1개에 대한 judge 평가 전체"""

    interest: str                     # 흥미 있는 부분
    blocks: tuple[BlockScore, ...]    # block 스코어 tuple
    canvas_score: float               # judge_score
    min_block_score: float            # 최소 block 값
    guard_triggered: bool             # 과락 존재 여부 판단 (min_guard가 발동했는지)
    verdict: Verdict                  # overall_verdict

    def dimension_means(self) -> dict[str, float]:
        """차원별 9칸 평균 - Judge 성능 평가를 위함 (사람이 채점한 것과 동일한지)"""
        return {
            dim: sum(getattr(b.raw, dim) for b in self.blocks) / len(self.blocks)
            for dim in DIMENSIONS
        }


@dataclass(frozen=True)
class SelfConsistencyResult:
    """동일 캔버스 N회 채점 결과 - Judge 성능 평가를 위함"""

    evaluations: tuple[CanvasEvaluation, ...]
    per_dimension_std: dict[str, float]  # 차원별 표준편차
    canvas_score_std: float
    passed: bool                         # 모든 σ <= SELF_CONSISTENCY_MAX_STD

    @property
    def n_runs(self) -> int:
        """실행 횟수"""
        return len(self.evaluations)

    @property
    def canvas_scores(self) -> tuple[float, ...]:
        """점수 모음"""
        return tuple(e.canvas_score for e in self.evaluations)

    @property
    def mean_canvas_score(self) -> float:
        """평균 캔버스 점수"""
        return sum(self.canvas_scores) / self.n_runs

    def dimension_means(self) -> dict[str, float]:
        """전체 런에 걸친 차원별 평균"""
        return {
            dim: sum(e.dimension_means()[dim] for e in self.evaluations) / self.n_runs
            for dim in DIMENSIONS
        }

    def majority_verdict(self) -> Verdict:
        """N회 판정의 다수결, 동률이면 더 보수적인 판정"""
        counts = Counter(e.verdict for e in self.evaluations)
        best = max(counts.items(), key=lambda kv: (kv[1], -_VERDICT_ORDER[kv[0]]))
        return best[0]


@dataclass(frozen=True)
class PairwiseResult:
    """두 캔버스 비교 결과 — 순서를 바꿔 2회 질의한 합산으로 판정"""

    winner: str               # "A" | "B" | "tie" (정/역 판정 불일치 시 tie)
    first_pass: str           # 원순서(A 먼저) 제시 시 판정 — "A" | "B"
    swapped_pass: str         # 순서 교체 제시 시 판정 — 원답안 기준으로 환산
    position_consistent: bool # 두 판정의 일치 여부 
    rationale: str = ""


@dataclass(frozen=True)
class EvalDatasetItem:
    """평가 데이터셋 항목 — 두 겹의 라벨

    human_scores는 이 아이디어로 *생성된 캔버스*를 사람이 4차원으로 채점한
    값({차원: 1~5})이며, 미채점이면 None. judge 점수(차원별 9칸 평균)와
    대조해 MAE·편향(6.4a)을 계산한다.
    """

    id: str                                     
    idea: str                                   
    category: str                               # good | bad | ambiguous
    expected_verdict: Verdict                   # 범주 라벨 — overall_verdict와 대조
    human_scores: dict[str, int] | None = None  # 생성된 캔버스를 사람이 채점한 값
    notes: str = ""


@dataclass(frozen=True)
class HumanAgreementResult:
    """judge 점수 vs 사람 점수 일치도 확인"""

    mae: float                  # 평균절대오차
    within_one_ratio: float     # |judge-사람| <= 1 비율
    signed_bias: float          # 부호 있는 (judge-사람) 평균 — 후함/박함의 방향
    n_compared: int             # 비교된 (항목 x 차원) 점수 쌍 수
    mae_pass: bool              # 패스 여부 3종
    within_one_pass: bool
    bias_pass: bool
