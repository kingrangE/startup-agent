"""Facade 패턴"""

from __future__ import annotations

from lean_canvas.llm.base import LLMClient
from lean_canvas.models import LeanCanvas
from lean_canvas.prompts import LeanCanvasPromptBuilder


class LeanCanvasGenerator:
    """
    프롬프트 조립 → LLM 호출 → 모델 변환 흐름을 하나의 진입점으로 묶는 Facade

    LLMClient는 생성자 주입으로 받아 구현체에 의존하지 않는다.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def generate(
        self,
        interest: str,
        extra_instructions: list[str] | None = None,
    ) -> LeanCanvas:
        """창업 관심사를 받아 린 캔버스 생성

        Args:
            interest: 사용자의 창업 관심사 (예: "반려동물 헬스케어").
            extra_instructions: 선택적 추가 지침 목록.

        Raises:
            ValueError: 관심사가 비어 있는 경우.
            LLMError: LLM 호출/파싱 실패 시.
        """
        if not interest or not interest.strip(): 
            raise ValueError("창업 관심사를 입력해 주세요.")

        builder = LeanCanvasPromptBuilder().with_interest(interest) 
        for instruction in extra_instructions or []:
            builder.with_instruction(instruction) # 추가 지침이 존재하는 경우 등록

        messages = builder.build() # build로 AI에 입력할 message 구성
        raw = self._llm_client.complete_json(messages) # message를 넣어 결과 응답 받음
        return LeanCanvas.from_dict(interest=interest.strip(), data=raw) # 관심사와 응답 반환
