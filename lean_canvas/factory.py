"""의존성 조립"""

from __future__ import annotations

import os

from lean_canvas.generator import LeanCanvasGenerator
from lean_canvas.llm.openai_client import OpenAILLMClient


def create_generator(
    api_key: str | None = None,
    model: str | None = None,
) -> LeanCanvasGenerator:
    """
    환경설정 파일을 읽어 LeanCanvasGenerator 제작

    인자 -> 환경변수 -> 기본값 순으로 진행
    """
    resolved_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_key:
        raise RuntimeError(
            "OpenAI API 키가 없습니다. OPENAI_API_KEY 환경변수를 설정하거나 "
            ".env 파일에 추가해 주세요."
        )
    resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    llm_client = OpenAILLMClient(api_key=resolved_key, model=resolved_model)
    return LeanCanvasGenerator(llm_client=llm_client)
