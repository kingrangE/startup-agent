from __future__ import annotations

from lean_canvas.evaluation.rubric import DIMENSIONS, rubric_table_text
from lean_canvas.models import LeanCanvas

# 기본 few-shot 앵커
DEFAULT_FEW_SHOT: tuple[str, ...] = (
    '진술 "모두를 위한 혁신 플랫폼" → specificity 1점 (대상·맥락 없음), '
    "evidence 1점 (근거 전무), differentiation 1점 (구분 안 됨)",
    '진술 "프리랜서 디자이너의 견적 작성을 평균 30분에서 5분으로 단축, '
    '사전 인터뷰 12건으로 확인" → specificity 5점 (검증 가능한 정량 진술), '
    "evidence 3점 (정성적 근거 1개)",
)


class JudgePromptBuilder:
    """
    린 캔버스 채점 프롬프트 Builder

    rubric.py의 앵커표를 시스템 프롬프트에 넣고, 
    채점 대상 캔버스와 출력 스키마를 사용자 프롬프트로 만든다.
    """

    def __init__(self) -> None:
        self._canvas: LeanCanvas | None = None
        self._few_shot_examples: list[str] = []
        self._retry_feedback: str = ""

    def with_canvas(self, canvas: LeanCanvas) -> "JudgePromptBuilder":
        """채점 대상 캔버스 등록"""
        self._canvas = canvas
        return self

    def with_few_shot(self, example: str) -> "JudgePromptBuilder":
        """점수대 앵커링용 채점 예시 등록"""
        self._few_shot_examples.append(example.strip())
        return self

    def with_retry_feedback(self, feedback: str) -> "JudgePromptBuilder":
        """직전 응답의 스키마 위반 내용 등록 — 재시도 시 self-correction 유도"""
        self._retry_feedback = feedback.strip()
        return self

    def build_system_prompt(self) -> str:
        """채점자 역할 + 전체 앵커표 + few-shot 예시로 시스템 프롬프트 생성"""
        rubric_text = "\n\n".join(rubric_table_text(dim) for dim in DIMENSIONS)

        few_shot = ""
        if self._few_shot_examples:
            joined = "\n".join(f"- {e}" for e in self._few_shot_examples)
            few_shot = f"\n\n[채점 예시]\n{joined}"

        return (
            "당신은 스타트업 린 캔버스를 채점하는 엄격한 심사위원입니다. "
            "아래 4개 차원의 1~5점 기준표에 따라 각 블록을 채점합니다. "
            "기준표에 정의된 수준에 정확히 대응하는 점수만 부여하며, "
            "인상이 아니라 기준 충족 여부로 판단합니다. "
            "출처·수치·전문용어가 등장하더라도 그 사실성과 검증 가능성이 "
            "의심되면 근거성(evidence) 점수를 높이지 마십시오. "
            "반드시 JSON 객체만 출력합니다.\n\n"
            f"[채점 기준표]\n{rubric_text}{few_shot}"
        )

    def build_user_prompt(self) -> str:
        """채점 대상 캔버스 + 출력 JSON 스키마로 사용자 프롬프트 생성"""
        if self._canvas is None:
            raise ValueError("채점 대상 캔버스(canvas)가 설정되지 않았습니다.")

        titles = LeanCanvas.block_titles()
        lines = [f"창업 관심사: {self._canvas.interest}"]
        for key, value in self._canvas.blocks().items():
            lines.append(f"\n[{key}] {titles[key]}")
            if isinstance(value, list):
                lines.extend(f"- {item}" for item in value)
            else:
                lines.append(f"- {value}")
        canvas_text = "\n".join(lines)

        block_schema = (
            '{"specificity": 1~5 정수, "evidence": 1~5 정수, '
            '"coherence": 1~5 정수, "differentiation": 1~5 정수, '
            '"rationale": "한두 문장의 채점 근거"}'
        )
        schema_lines = ",\n".join(f'  "{key}": {block_schema}' for key in titles)

        retry_note = ""
        if self._retry_feedback:
            retry_note = (
                "\n\n[주의] 직전 응답이 스키마를 위반했습니다. "
                f"위반 내용: {self._retry_feedback}\n"
                "위 스키마를 정확히 지켜 다시 채점하세요."
            )

        return f"""다음 린 캔버스의 9개 블록을 각각 4개 차원으로 채점해 주세요.

[채점 대상 린 캔버스]
{canvas_text}

[출력 형식]
아래 JSON 스키마를 정확히 따라 9개 블록 모두에 대해 JSON 객체만 출력하세요.
{{
{schema_lines}
}}

[채점 원칙]
- 점수는 반드시 1~5 사이의 정수일 것
- coherence는 해당 블록이 다른 블록들과 논리적으로 정합한지를 볼 것
- rationale에는 점수의 근거가 된 기준표 항목을 언급할 것{retry_note}"""

    def build(self) -> list[dict[str, str]]:
        """메시지 리스트 생성"""
        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": self.build_user_prompt()},
        ]
