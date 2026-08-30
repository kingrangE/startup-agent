from __future__ import annotations

import pytest

from lean_canvas.llm.base import LLMError
from separk.llm.ax_client import AXModelClient


def test_ax_model_defaults_to_required_skt_model():
    assert AXModelClient().model_id == "skt/A.X-4.0-Light"


def test_ax_json_extraction_handles_markdown_fence():
    assert AXModelClient._extract_json('```json\n{"ok": true}\n```') == {"ok": True}


def test_ax_json_extraction_rejects_non_json():
    with pytest.raises(LLMError, match="JSON 객체"):
        AXModelClient._extract_json("결과 없음")


class FakeTensor:
    shape = (1, 3)


class FakeEncoding(dict):
    def __init__(self):
        super().__init__(input_ids=FakeTensor())
        self.moved_to = None

    def to(self, device):
        self.moved_to = device
        return self


class FakeTokenizer:
    def __init__(self):
        self.encoding = FakeEncoding()

    def apply_chat_template(self, *args, **kwargs):
        assert kwargs["add_generation_prompt"] is True
        return self.encoding

    def decode(self, tokens, skip_special_tokens=True):
        assert tokens == [4, 5]
        return '{"canvas": {}, "claims": []}'


class FakeModel:
    device = "cpu"

    def generate(self, **kwargs):
        assert kwargs["max_new_tokens"] == 8
        assert kwargs["do_sample"] is False
        return [[1, 2, 3, 4, 5]]


def test_ax_client_runs_injected_transformers_contract_without_download():
    tokenizer = FakeTokenizer()
    client = AXModelClient(tokenizer=tokenizer, model=FakeModel(), max_new_tokens=8)
    result = client.complete_json([{"role": "user", "content": "테스트"}])
    assert result == {"canvas": {}, "claims": []}
    assert tokenizer.encoding.moved_to == "cpu"
