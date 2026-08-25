"""의존성 조립"""

from __future__ import annotations

import os

from lean_canvas.evaluation.judge import CanvasJudge
from lean_canvas.evaluation.pairwise import PairwiseJudge
from lean_canvas.generator import LeanCanvasGenerator
from lean_canvas.llm.openai_client import OpenAILLMClient


_DEFAULT_GENERATOR_MODEL = "gpt-4o-mini"
_DEFAULT_JUDGE_MODEL = "gpt-4o"
_GENERATION_TEMPERATURE = 0.7
_EVALUATION_TEMPERATURE = 0.0
_MISSING_API_KEY_MESSAGE = (
    "OpenAI API 키가 없습니다. OPENAI_API_KEY 환경변수를 설정하거나 "
    ".env 파일에 추가해 주세요."
)


def _resolve_api_key(api_key: str | None) -> str:
    """Resolve the shared OpenAI credential policy for every factory."""
    resolved_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_key:
        raise RuntimeError(_MISSING_API_KEY_MESSAGE)
    return resolved_key


def _create_llm_client(
    *,
    api_key: str | None,
    model: str | None,
    model_environment: str,
    default_model: str,
    temperature: float,
) -> OpenAILLMClient:
    """Build an OpenAI client from argument, environment, and default values."""
    resolved_model = model or os.getenv(model_environment, default_model)
    return OpenAILLMClient(
        api_key=_resolve_api_key(api_key),
        model=resolved_model,
        temperature=temperature,
    )


def create_generator(
    api_key: str | None = None,
    model: str | None = None,
) -> LeanCanvasGenerator:
    """Create a canvas generator from explicit or environment configuration.

    Model priority is ``model`` -> ``OPENAI_MODEL`` -> ``gpt-4o-mini``.
    Generation keeps the client default temperature of 0.7.
    """
    llm_client = _create_llm_client(
        api_key=api_key,
        model=model,
        model_environment="OPENAI_MODEL",
        default_model=_DEFAULT_GENERATOR_MODEL,
        temperature=_GENERATION_TEMPERATURE,
    )
    return LeanCanvasGenerator(llm_client=llm_client)


def create_judge(
    api_key: str | None = None,
    model: str | None = None,
) -> CanvasJudge:
    """Create a canvas judge with deterministic evaluation settings.

    Model priority is ``model`` -> ``JUDGE_MODEL`` -> ``gpt-4o``.
    Temperature is fixed at 0.0 so repeated evaluation is not affected by
    sampling configuration hidden in the client default.
    """
    llm_client = _create_llm_client(
        api_key=api_key,
        model=model,
        model_environment="JUDGE_MODEL",
        default_model=_DEFAULT_JUDGE_MODEL,
        temperature=_EVALUATION_TEMPERATURE,
    )
    return CanvasJudge(llm_client=llm_client)


def create_pairwise_judge(
    api_key: str | None = None,
    model: str | None = None,
) -> PairwiseJudge:
    """Create a pairwise judge using the shared deterministic judge policy.

    Model priority is ``model`` -> ``JUDGE_MODEL`` -> ``gpt-4o`` and the
    evaluation temperature is fixed at 0.0.
    """
    llm_client = _create_llm_client(
        api_key=api_key,
        model=model,
        model_environment="JUDGE_MODEL",
        default_model=_DEFAULT_JUDGE_MODEL,
        temperature=_EVALUATION_TEMPERATURE,
    )
    return PairwiseJudge(llm_client=llm_client)
