"""파이프라인 검증용 스모크 테스트"""

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


generator = LeanCanvasGenerator(llm_client=FakeLLMClient())
canvas = generator.generate("반려동물 헬스케어", extra_instructions=["국내 시장 한정"])

assert canvas.problem == ["문제1", "문제2"]
assert canvas.unfair_advantage == "경쟁 우위"  # 보정 확인
assert "린 캔버스" in ConsoleRenderer().render(canvas)
assert "## 문제 (Problem)" in MarkdownRenderer().render(canvas)

# 빈 입력 검증
try:
    generator.generate("  ")
    raise AssertionError("빈 입력이 통과됨")
except ValueError:
    pass

print(ConsoleRenderer().render(canvas))
print("\nALL SMOKE TESTS PASSED")
