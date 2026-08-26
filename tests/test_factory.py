"""Factory dependency wiring contracts."""

from __future__ import annotations

from collections.abc import Callable

import pytest

import lean_canvas.factory as factory
from lean_canvas.evaluation.judge import CanvasJudge
from lean_canvas.evaluation.pairwise import PairwiseJudge
from lean_canvas.generator import LeanCanvasGenerator


Factory = Callable[..., LeanCanvasGenerator | CanvasJudge | PairwiseJudge]


@pytest.fixture
def client_configs(monkeypatch) -> list[dict[str, object]]:
    """Replace the OpenAI client so factory tests never make network calls."""
    configs: list[dict[str, object]] = []

    class RecordingOpenAIClient:
        def __init__(self, **kwargs: object) -> None:
            configs.append(kwargs)

    monkeypatch.setattr(factory, "OpenAILLMClient", RecordingOpenAIClient)
    return configs


@pytest.fixture(autouse=True)
def clean_factory_environment(monkeypatch) -> None:
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "JUDGE_MODEL"):
        monkeypatch.delenv(name, raising=False)


def test_factories_return_expected_facades(client_configs) -> None:
    assert isinstance(factory.create_generator(api_key="test-key"), LeanCanvasGenerator)
    assert isinstance(factory.create_judge(api_key="test-key"), CanvasJudge)
    assert isinstance(factory.create_pairwise_judge(api_key="test-key"), PairwiseJudge)
    assert len(client_configs) == 3


@pytest.mark.parametrize(
    ("builder", "expected_model", "expected_temperature"),
    [
        (factory.create_generator, "generator-env-model", 0.7),
        (factory.create_judge, "judge-env-model", 0.0),
        (factory.create_pairwise_judge, "judge-env-model", 0.0),
    ],
)
def test_environment_selects_role_specific_model(
    monkeypatch,
    client_configs,
    builder: Factory,
    expected_model: str,
    expected_temperature: float,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    monkeypatch.setenv("OPENAI_MODEL", "generator-env-model")
    monkeypatch.setenv("JUDGE_MODEL", "judge-env-model")

    builder()

    assert client_configs == [
        {
            "api_key": "environment-key",
            "model": expected_model,
            "temperature": expected_temperature,
        }
    ]


@pytest.mark.parametrize(
    "builder",
    [factory.create_generator, factory.create_judge, factory.create_pairwise_judge],
)
def test_explicit_configuration_overrides_environment(
    monkeypatch,
    client_configs,
    builder: Factory,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    monkeypatch.setenv("OPENAI_MODEL", "generator-env-model")
    monkeypatch.setenv("JUDGE_MODEL", "judge-env-model")

    builder(api_key="argument-key", model="argument-model")

    assert client_configs[0]["api_key"] == "argument-key"
    assert client_configs[0]["model"] == "argument-model"


@pytest.mark.parametrize(
    ("builder", "expected_model"),
    [
        (factory.create_generator, "gpt-4o-mini"),
        (factory.create_judge, "gpt-4o"),
        (factory.create_pairwise_judge, "gpt-4o"),
    ],
)
def test_factories_use_role_specific_default_models(
    client_configs,
    builder: Factory,
    expected_model: str,
) -> None:
    builder(api_key="test-key")

    assert client_configs[0]["model"] == expected_model


@pytest.mark.parametrize(
    "builder",
    [factory.create_generator, factory.create_judge, factory.create_pairwise_judge],
)
def test_factories_raise_consistent_error_without_api_key(builder: Factory) -> None:
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY") as error:
        builder()

    assert str(error.value) == (
        "OpenAI API 키가 없습니다. OPENAI_API_KEY 환경변수를 설정하거나 "
        ".env 파일에 추가해 주세요."
    )
