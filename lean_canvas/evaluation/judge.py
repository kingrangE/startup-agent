"""캔버스 채점 Facade — LeanCanvasGenerator와 동일한 구조

프롬프트 조립 → judge LLM 호출 → 스키마 검증 → 집계 흐름을 하나의
진입점으로 묶는다. LLMClient는 생성자 주입으로 받아 구현체에 의존하지 않는다.
"""

from __future__ import annotations

from statistics import pstdev

from lean_canvas.evaluation.aggregation import build_canvas_evaluation
from lean_canvas.evaluation.judge_prompts import DEFAULT_FEW_SHOT, JudgePromptBuilder
from lean_canvas.evaluation.models import (
    CanvasEvaluation,
    JudgeScore,
    SelfConsistencyResult,
)
from lean_canvas.evaluation.parsing import JudgeParseError, parse_judge_response
from lean_canvas.evaluation.rubric import DIMENSIONS, SELF_CONSISTENCY_MAX_STD
from lean_canvas.llm.base import LLMClient, LLMError
from lean_canvas.models import LeanCanvas


class CanvasJudge:
    """
    린 캔버스를 rubric 기준으로 채점하는 LLM-as-judge Facade 패턴

    9개 Block x 4개 기준 = 36개 점수를 단일 호출로 채점 (호출 비용 절감을 위함)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        few_shot_examples: tuple[str, ...] | None = None,
        max_retries: int = 2,
    ) -> None:
        self._llm_client = llm_client
        self._few_shot_examples = (
            DEFAULT_FEW_SHOT if few_shot_examples is None else few_shot_examples
        )
        self._max_retries = max_retries

    def score_once(self, canvas: LeanCanvas) -> dict[str, JudgeScore]:
        """
        1번 채점, 스키마 위반 응답이면 위반 내용을 추가하여 재시도
        
        Args :
            canvas: 린 캔버스
        Return :
            
        Raises:
            LLMError: API 호출 실패 또는 max_retries 초과 시
        """
        last_error: JudgeParseError | None = None
        for _ in range(self._max_retries + 1):
            builder = JudgePromptBuilder().with_canvas(canvas)
            for example in self._few_shot_examples:
                builder.with_few_shot(example)
            if last_error is not None:
                builder.with_retry_feedback(str(last_error))

            raw = self._llm_client.complete_json(builder.build())
            try:
                return parse_judge_response(raw)
            except JudgeParseError as e:
                last_error = e

        raise LLMError(
            f"judge 응답 스키마 검증 {self._max_retries + 1}회 실패: {last_error}"
        )

    def evaluate(self, canvas: LeanCanvas) -> CanvasEvaluation:
        """채점 + 집계(6.3)를 거쳐 평가 결과를 반환한다."""
        raw_scores = self.score_once(canvas)
        return build_canvas_evaluation(canvas.interest, raw_scores)

    def self_consistency(
        self,
        canvas: LeanCanvas,
        n: int = 5,
    ) -> SelfConsistencyResult:
        """동일 캔버스를 n회 채점해 점수 흔들림(σ)을 측정한다 (6.4a).

        차원별 σ는 "런별 9칸 평균"의 표준편차, 총점 σ는 canvas_score의
        표준편차. 모든 σ가 SELF_CONSISTENCY_MAX_STD 이하면 통과.
        """
        if n < 2:
            raise ValueError("self-consistency 측정에는 최소 2회 채점이 필요합니다.")

        evaluations = tuple(self.evaluate(canvas) for _ in range(n))

        per_dimension_std = {
            dim: pstdev([e.dimension_means()[dim] for e in evaluations])
            for dim in DIMENSIONS
        }
        canvas_score_std = pstdev([e.canvas_score for e in evaluations])
        passed = canvas_score_std <= SELF_CONSISTENCY_MAX_STD and all(
            std <= SELF_CONSISTENCY_MAX_STD for std in per_dimension_std.values()
        )
        return SelfConsistencyResult(
            evaluations=evaluations,
            per_dimension_std=per_dimension_std,
            canvas_score_std=canvas_score_std,
            passed=passed,
        )
