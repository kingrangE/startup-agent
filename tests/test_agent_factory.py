from __future__ import annotations

import pytest

from separk.agent.factory import create_agent_llm
from separk.llm.ax_client import AXModelClient


def test_agent_factory_defaults_to_ax(monkeypatch):
    monkeypatch.delenv("SEPARK_LLM_PROVIDER", raising=False)
    client = create_agent_llm()
    assert isinstance(client, AXModelClient)
    assert client.model_id == "skt/A.X-4.0-Light"


def test_agent_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="지원하지 않는"):
        create_agent_llm("unknown")
