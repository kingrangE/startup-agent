"""생성 파이프라인 스모크 테스트"""

from __future__ import annotations

import pytest

from lean_canvas.generator import LeanCanvasGenerator
from lean_canvas.llm.base import LLMClient
from lean_canvas.renderers import ConsoleRenderer, MarkdownRenderer


class FakeLLMClient(LLMClient):
    """고정 응답을 돌려주는 테스트용 Strategy 구현체"""

    def complete_json(self, messages: list[dict[str, str]]) -> dict:
        assert messages[0]["role"] == "system"
        assert "반려동물 헬스케어" in messages[1]["content"]
        return {
            "problem": ["문제1", "문제2"],
            "customer_segments": ["고객군1"],
            "unique_value_proposition": "가치 제안 한 문장",
            "solution": ["솔루션1", "솔루션2"],
            "channels": ["채널1"],
            "revenue_streams": ["수익원1"],
            "cost_structure": ["비용1"],
            "key_metrics": ["지표1"],
            "unfair_advantage": ["경쟁", "우위"],  # 리스트→문자열 보정 검증
        }


@pytest.fixture
def generated_canvas():
    generator = LeanCanvasGenerator(llm_client=FakeLLMClient())
    return generator.generate("반려동물 헬스케어", extra_instructions=["국내 시장 한정"])


def test_generate_converts_response_to_model(generated_canvas):
    assert generated_canvas.problem == ["문제1", "문제2"]
    assert generated_canvas.unfair_advantage == "경쟁 우위"  # 리스트→문자열 보정


def test_renderers_produce_expected_output(generated_canvas):
    assert "린 캔버스" in ConsoleRenderer().render(generated_canvas)
    assert "## 문제 (Problem)" in MarkdownRenderer().render(generated_canvas)


def test_empty_interest_raises():
    generator = LeanCanvasGenerator(llm_client=FakeLLMClient())
    with pytest.raises(ValueError):
        generator.generate("  ")
