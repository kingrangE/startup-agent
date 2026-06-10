"""
pairwise 비교 judge

두 캔버스 비교 평가, 위치 편향 방지를 위한 순서 변경 후 질문 로직 포함
"""

from __future__ import annotations

from lean_canvas.evaluation.models import PairwiseResult
from lean_canvas.evaluation.rubric import DIMENSION_TITLES_KO, DIMENSIONS
from lean_canvas.llm.base import LLMClient, LLMError
from lean_canvas.models import LeanCanvas


class PairwiseJudge:
    """
    두 린 캔버스의 우위 직접 judge

    compare()는 순서를 바꾸며 2회 질의 (위치 편향 방지)
    """

    def __init__(self, llm_client: LLMClient, max_retries: int = 2) -> None:
        self._llm_client = llm_client
        self._max_retries = max_retries

    def compare(self, canvas_a: LeanCanvas, canvas_b: LeanCanvas) -> PairwiseResult:
        """A/B 두 캔버스를 순서를 바꿔 2회 비교

        Args:
            canvas_a: 린캔버스 앞
            canvas_b: 린캔버스 뒤
        Returns:
            PairwiseResult — 두 판정이 일치하면 승자
            뒤집히면 winner="tie", position_consistent=False.
        """
        first_choice, first_rationale = self._ask(canvas_a, canvas_b)
        swapped_choice, swapped_rationale = self._ask(canvas_b, canvas_a)

        # 원순서: 답안1=A, 답안2=B / 교체 제시: 답안1=B, 답안2=A → 원답안 기준 환산
        first_pass = "A" if first_choice == "1" else "B"
        swapped_pass = "B" if swapped_choice == "1" else "A"

        consistent = first_pass == swapped_pass
        return PairwiseResult(
            winner=first_pass if consistent else "tie",
            first_pass=first_pass,
            swapped_pass=swapped_pass,
            position_consistent=consistent,
            rationale=f"1차(원순서): {first_rationale} / 2차(교체): {swapped_rationale}",
        )

    def _ask(self, first: LeanCanvas, second: LeanCanvas) -> tuple[str, str]:
        """
        제시 순서대로 두 캔버스를 비교 질의
        Args:
            first: 앞 린 캔버스
            second: 뒤 린 캔버스
        Return:
            ("1"|"2", 근거)
        Raises:
            LLMError: 응답이 max_retries 초과로 스키마를 위반한 경우
        """
        messages = self._build_messages(first, second)
        last_error = ""
        for _ in range(self._max_retries + 1):
            raw = self._llm_client.complete_json(messages)
            winner = str(raw.get("winner", "")).strip()
            if winner in ("1", "2"):
                return winner, str(raw.get("rationale", ""))
            last_error = f'winner가 "1" 또는 "2"가 아닙니다: {raw.get("winner")!r}'

        raise LLMError(
            f"pairwise 응답 검증 {self._max_retries + 1}회 실패: {last_error}"
        )

    def _build_messages(
        self,
        first: LeanCanvas,
        second: LeanCanvas,
    ) -> list[dict[str, str]]:
        """비교 프롬프트 생성, rubric의 평가 기준 그대로 사용"""
        criteria = ", ".join(DIMENSION_TITLES_KO[dim] for dim in DIMENSIONS)
        system = (
            "당신은 두 개의 스타트업 린 캔버스 답안을 비교 평가하는 심사위원입니다. "
            f"{criteria} 4개 차원을 종합해 어느 답안이 전반적으로 더 나은지 "
            "반드시 하나를 선택합니다. 무승부는 허용되지 않습니다. "
            "반드시 JSON 객체만 출력합니다."
        )
        user = f"""다음 두 린 캔버스 답안 중 어느 쪽이 더 나은지 판정해 주세요.

[답안 1]
{self._render(first)}

[답안 2]
{self._render(second)}

[출력 형식]
{{"winner": "1" 또는 "2", "rationale": "한두 문장의 판정 근거"}}"""
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    @staticmethod
    def _render(canvas: LeanCanvas) -> str:
        """비교 제시용 캔버스 텍스트 렌더"""
        titles = LeanCanvas.block_titles()
        lines = [f"창업 관심사: {canvas.interest}"]
        for key, value in canvas.blocks().items():
            lines.append(f"[{titles[key]}]")
            if isinstance(value, list):
                lines.extend(f"- {item}" for item in value)
            else:
                lines.append(f"- {value}")
        return "\n".join(lines)
