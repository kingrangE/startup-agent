"""테스트 공용 헬퍼 — Fake LLM 클라이언트와 judge 응답 팩토리"""

from __future__ import annotations

from lean_canvas.evaluation.rubric import DIMENSIONS
from lean_canvas.llm.base import LLMClient
from lean_canvas.models import LeanCanvas


class ScriptedLLMClient(LLMClient):
    """등록된 응답을 순서대로 반환하는 테스트용 Strategy 구현체

    N회 채점(self-consistency), 정/역 pairwise처럼 
    호출마다 다른 응답이 필요한 시나리오 재현 호출된 메시지는 calls 기록
    """

    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    def complete_json(self, messages: list[dict[str, str]]) -> dict:
        self.calls.append(messages) # 호출한 message 삽입
        if not self._responses: # 자동 반환할 응답 존재 확인
            raise AssertionError("준비된 응답이 더 이상 없습니다.")
        return self._responses.pop(0) # 응답 list pop


def make_judge_response(
    score: int = 4,
    overrides: dict[str, dict[str, int]] | None = None,
    rationale: str = "기준표 근거",
) -> dict:
    """9블록 x 4차원 judge 응답 JSON 생성 Factory

    Args:
        score: 모든 차원에 일괄 적용할 기본 점수
        overrides: {블록키: {차원: 점수}} 형태의 부분 덮어쓰기
    """
    response: dict = {}
    for key in LeanCanvas.block_titles():
        response[key] = {dim: score for dim in DIMENSIONS}
        response[key]["rationale"] = rationale
    for block_key, dims in (overrides or {}).items():
        response[block_key].update(dims)
    return response
