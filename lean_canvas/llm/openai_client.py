"""OpenAI API 구현체."""

from __future__ import annotations

import json

from openai import OpenAI, OpenAIError

from lean_canvas.llm.base import LLMClient, LLMError


class OpenAILLMClient(LLMClient):
    """OpenAI Chat Completions API를 사용"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ) -> None:
        # api_key가 None이면 OPENAI_API_KEY 환경변수를 사용한다.
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature

    def complete_json(self, messages: list[dict[str, str]]) -> dict:
        """message를 입력받아 출력"""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                response_format={"type": "json_object"},
            )
        except OpenAIError as e:
            raise LLMError(f"OpenAI API 호출 실패: {e}") from e

        content = response.choices[0].message.content
        if not content:
            raise LLMError("OpenAI API가 빈 응답을 반환했습니다.")

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMError(f"응답 JSON 파싱 실패: {e}\n응답 내용: {content[:500]}") from e
