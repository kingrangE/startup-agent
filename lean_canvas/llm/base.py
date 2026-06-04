"""LLM 클라이언트 추상화"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(Exception):
    """LLM 호출 실패 예외 클래스"""


class LLMClient(ABC):
    """
    LLM Provider 공통 인터페이스

    OpenAI외 다른 Provider로 교체 시, 해당 인터페이스만 구현하면 된다.
    """

    @abstractmethod
    def complete_json(self, messages: list[dict[str, str]]) -> dict:
        """메시지를 전달하고 JSON 응답을 dict로 반환한다.

        Raises:
            LLMError: API 호출 실패 또는 JSON 파싱 실패 시.
        """
        raise NotImplementedError
