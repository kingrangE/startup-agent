from __future__ import annotations

import json

import pytest

from separk.agent.models import SearchResult
from separk.agent.search import (
    CompositeSearchProvider,
    GoogleSearchProvider,
    canonical_url,
)


class StubProvider:
    def __init__(self, name: str, rows: list[SearchResult]) -> None:
        self.name = name
        self.rows = rows
        self.queries: list[str] = []

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        return self.rows[:max_results]


def test_canonical_url_removes_tracking_and_fragments():
    assert (
        canonical_url("HTTPS://Example.com/a/?utm_source=x&b=2#top")
        == "https://example.com/a?b=2"
    )
    assert canonical_url("javascript:alert(1)") == ""


def test_composite_search_uses_both_providers_and_deduplicates():
    shared_google = SearchResult(
        "google", "G", "https://example.com/a?utm_source=g", "근거", "q"
    )
    shared_ddg = SearchResult("duckduckgo", "D", "https://example.com/a", "중복", "q")
    unique = SearchResult("duckduckgo", "U", "https://example.com/b", "추가", "q")
    google = StubProvider("google", [shared_google])
    ddg = StubProvider("duckduckgo", [shared_ddg, unique])

    rows = CompositeSearchProvider((google, ddg)).search_many(("시장",), max_results=5)

    assert [row.url for row in rows] == [shared_google.url, unique.url]
    assert google.queries == ["시장"]
    assert ddg.queries == ["시장"]


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return json.dumps(
            {
                "items": [
                    {
                        "title": "시장 자료",
                        "link": "https://example.com",
                        "snippet": "검증 근거",
                    }
                ]
            }
        ).encode()


def test_google_search_maps_custom_search_response(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return FakeHTTPResponse()

    monkeypatch.setattr("separk.agent.search.urlopen", fake_urlopen)
    rows = GoogleSearchProvider("secret", "engine", timeout=3).search(
        "반려동물 시장", 2
    )
    assert len(rows) == 1
    assert rows[0].provider == "google"
    assert rows[0].snippet == "검증 근거"
    assert "key=secret" in seen["url"]
    assert "cx=engine" in seen["url"]
    assert seen["timeout"] == 3


def test_google_search_error_does_not_leak_api_key(monkeypatch):
    def fail(request, timeout):
        raise OSError(f"failed URL {request.full_url}")

    monkeypatch.setattr("separk.agent.search.urlopen", fail)
    with pytest.raises(Exception) as caught:
        GoogleSearchProvider("top-secret", "engine").search("시장")
    assert "top-secret" not in str(caught.value)
