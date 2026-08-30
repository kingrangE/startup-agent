"""Local Hugging Face adapter for SK Telecom A.X 4.0 Light."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from lean_canvas.llm.base import LLMClient, LLMError


class AXModelClient(LLMClient):
    """Run ``skt/A.X-4.0-Light`` locally through Transformers.

    Model loading is lazy and injectable so unit tests never download weights.
    """

    DEFAULT_MODEL_ID = "skt/A.X-4.0-Light"

    def __init__(
        self,
        model_id: str | None = None,
        *,
        device_map: str | None = None,
        max_new_tokens: int | None = None,
        tokenizer: Any | None = None,
        model: Any | None = None,
    ) -> None:
        self.model_id = model_id or os.getenv("AX_MODEL_ID", self.DEFAULT_MODEL_ID)
        self.device_map = device_map or os.getenv("AX_DEVICE_MAP", "auto")
        self.max_new_tokens = max_new_tokens or int(
            os.getenv("AX_MAX_NEW_TOKENS", "4096")
        )
        self._tokenizer = tokenizer
        self._model = model

    def _load(self) -> tuple[Any, Any]:
        if self._tokenizer is not None and self._model is not None:
            return self._tokenizer, self._model
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise LLMError(
                "A.X 로컬 모델을 사용하려면 local extra를 설치하세요: "
                '`python -m pip install -e ".[local]"`'
            ) from exc
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype="auto",
                device_map=self.device_map,
            )
        except Exception as exc:
            raise LLMError(f"A.X 모델 로딩 실패 ({self.model_id}): {exc}") from exc
        return self._tokenizer, self._model

    @staticmethod
    def _extract_json(text: str) -> dict:
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE
        )
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start < 0 or end <= start:
                raise LLMError(
                    f"A.X 응답에서 JSON 객체를 찾지 못했습니다: {cleaned[:300]}"
                ) from None
            try:
                payload = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise LLMError(
                    f"A.X JSON 파싱 실패: {exc}; 응답={cleaned[:300]}"
                ) from exc
        if not isinstance(payload, dict):
            raise LLMError("A.X 응답의 최상위 값은 JSON 객체여야 합니다.")
        return payload

    def complete_json(self, messages: list[dict[str, str]]) -> dict:
        tokenizer, model = self._load()
        try:
            encoded = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_tensors="pt",
                return_dict=True,
            )
            if hasattr(encoded, "to") and hasattr(model, "device"):
                encoded = encoded.to(model.device)
            generated = model.generate(
                **encoded,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )
            input_length = encoded["input_ids"].shape[-1]
            text = tokenizer.decode(
                generated[0][input_length:], skip_special_tokens=True
            )
        except Exception as exc:
            raise LLMError(f"A.X 추론 실패: {exc}") from exc
        return self._extract_json(text)
