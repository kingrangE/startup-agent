"""린 캔버스 생성 프롬프트"""

from __future__ import annotations


class LeanCanvasPromptBuilder:
    """창업 관심사를 바탕으로 LLM에 전달할 프롬프트를 단계적으로 제작

    Builder 패턴: 시스템 역할, 출력 스키마, 작성 지침, 사용자 입력을
    각 메서드로 나누어 조립하고 build()로 최종 메시지를 생성한다.
    """

    def __init__(self) -> None:
        self._interest: str = ""
        self._language: str = "한국어"
        self._extra_instructions: list[str] = []

    def with_interest(self, interest: str) -> "LeanCanvasPromptBuilder":
        # 관심사 등록
        self._interest = interest.strip()
        return self

    def with_language(self, language: str) -> "LeanCanvasPromptBuilder":
        # 언어 등록
        self._language = language
        return self

    def with_instruction(self, instruction: str) -> "LeanCanvasPromptBuilder":
        # 추가 지침 등록
        self._extra_instructions.append(instruction.strip())
        return self

    def build_system_prompt(self) -> str:
        """
        System Prompt 생성
        """
        return (
            "당신은 수많은 스타트업의 사업 모델 설계를 도운 전문 컨설턴트입니다. "
            "사용자의 창업 관심사를 분석하여 구체적이고 실행 가능한 "
            "린 캔버스(Lean Canvas)를 작성합니다. "
            f"모든 내용은 {self._language}로 작성하며, 막연한 표현 대신 "
            "검증 가능한 가설 수준의 구체적인 문장으로 작성합니다. "
            "반드시 JSON 객체만 출력합니다."
        )

    def build_user_prompt(self) -> str:
        """
        등록된 정보를 바탕으로 user prompt 생성
        """
        if not self._interest:
            raise ValueError("창업 관심사(interest)가 설정되지 않았습니다.")

        instructions = ""
        if self._extra_instructions:
            joined = "\n".join(f"- {i}" for i in self._extra_instructions)
            instructions = f"\n\n[추가 지침]\n{joined}"

        return f"""다음 창업 관심사를 바탕으로 린 캔버스를 작성해 주세요.

[창업 관심사]
{self._interest}{instructions}

[출력 형식]
아래 JSON 스키마를 정확히 따라 JSON 객체만 출력하세요.
{{
  "problem": ["고객이 겪는 핵심 문제 2~3개"],
  "customer_segments": ["목표 고객군 2~3개 (얼리어답터 명시)"],
  "unique_value_proposition": "한 문장의 명확한 차별화 메시지",
  "solution": ["각 문제에 대응하는 솔루션 2~3개"],
  "channels": ["고객 도달 경로 2~3개"],
  "revenue_streams": ["수익 모델 2~3개"],
  "cost_structure": ["주요 비용 항목 2~3개"],
  "key_metrics": ["측정할 핵심 지표 2~3개"],
  "unfair_advantage": "쉽게 모방할 수 없는 경쟁 우위 한 문장"
}}

[작성 원칙]
- 각 항목은 해당 관심사 도메인의 실제 시장 상황을 반영할 것
- 문제와 솔루션은 1:1로 대응되도록 작성할 것
- 핵심 지표는 측정 가능한 수치 기반 지표로 작성할 것"""

    def build(self) -> list[dict[str, str]]:
        """OpenAI Chat API 형식의 메시지 리스트 생성"""
        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": self.build_user_prompt()},
        ]
