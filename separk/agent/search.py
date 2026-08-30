"""Google and DuckDuckGo retrieval with deterministic deduplication."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from separk.agent.models import SearchResult


class SearchError(RuntimeError):
    """A configured search provider could not complete a request."""


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return ""
    filtered = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"gclid", "fbclid"}
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(filtered), "")
    )


class GoogleSearchProvider:
    """Google Programmable Search JSON API adapter."""

    name = "google"
    endpoint = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, cse_id: str, timeout: float = 10.0) -> None:
        if not api_key or not cse_id:
            raise ValueError(
                "Google 검색에는 GOOGLE_API_KEY와 GOOGLE_CSE_ID가 필요합니다."
            )
        self._api_key = api_key
        self._cse_id = cse_id
        self._timeout = timeout

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        params = urlencode(
            {
                "key": self._api_key,
                "cx": self._cse_id,
                "q": query,
                "num": min(max_results, 10),
            }
        )
        request = Request(
            f"{self.endpoint}?{params}", headers={"User-Agent": "SePark/0.2"}
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # never echo a URL containing the Google API key
            raise SearchError(f"Google 검색 실패 ({type(exc).__name__})") from exc

        return [
            SearchResult(
                provider=self.name,
                title=str(item.get("title", "")),
                url=str(item.get("link", "")),
                snippet=str(item.get("snippet", "")),
                query=query,
            )
            for item in payload.get("items", [])[:max_results]
            if item.get("link")
        ]


class DuckDuckGoSearchProvider:
    """DuckDuckGo adapter backed by the maintained ``ddgs`` package."""

    name = "duckduckgo"

    def __init__(self, region: str = "kr-kr", safesearch: str = "moderate") -> None:
        self._region = region
        self._safesearch = safesearch

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        try:
            from ddgs import DDGS

            rows = DDGS().text(
                query,
                region=self._region,
                safesearch=self._safesearch,
                max_results=max_results,
            )
        except Exception as exc:
            raise SearchError(f"DuckDuckGo 검색 실패: {exc}") from exc

        return [
            SearchResult(
                provider=self.name,
                title=str(row.get("title", "")),
                url=str(row.get("href", row.get("url", ""))),
                snippet=str(row.get("body", row.get("snippet", ""))),
                query=query,
            )
            for row in rows
            if row.get("href") or row.get("url")
        ]


@dataclass
class CompositeSearchProvider:
    providers: tuple[SearchProvider, ...]
    fail_if_all_providers_fail: bool = True

    @property
    def name(self) -> str:
        return "+".join(provider.name for provider in self.providers)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        return self.search_many((query,), max_results=max_results)

    def search_many(
        self, queries: Iterable[str], max_results: int = 5
    ) -> list[SearchResult]:
        tasks = [
            (query_index, provider_index, query, provider)
            for query_index, query in enumerate(queries)
            for provider_index, provider in enumerate(self.providers)
        ]
        if not tasks:
            raise SearchError("활성화된 검색 공급자가 없습니다.")

        indexed_results: list[tuple[int, int, list[SearchResult]]] = []
        failures: list[str] = []
        with ThreadPoolExecutor(max_workers=min(8, len(tasks))) as executor:
            futures = {
                executor.submit(provider.search, query, max_results): (
                    qi,
                    pi,
                    provider.name,
                )
                for qi, pi, query, provider in tasks
            }
            for future in as_completed(futures):
                query_index, provider_index, provider_name = futures[future]
                try:
                    indexed_results.append(
                        (query_index, provider_index, future.result())
                    )
                except SearchError as exc:
                    failures.append(f"{provider_name}: {exc}")

        if not indexed_results and self.fail_if_all_providers_fail:
            raise SearchError("모든 검색 공급자가 실패했습니다: " + "; ".join(failures))

        deduped: list[SearchResult] = []
        seen: set[str] = set()
        for _, _, rows in sorted(indexed_results, key=lambda item: (item[0], item[1])):
            for row in rows:
                key = canonical_url(row.url)
                if not key or key in seen:
                    continue
                seen.add(key)
                deduped.append(row)
        return deduped


def create_search_provider(
    *,
    google_api_key: str | None = None,
    google_cse_id: str | None = None,
    require_google: bool = False,
) -> CompositeSearchProvider:
    key = google_api_key or os.getenv("GOOGLE_API_KEY")
    cse = google_cse_id or os.getenv("GOOGLE_CSE_ID")
    providers: list[SearchProvider] = []
    if key and cse:
        providers.append(GoogleSearchProvider(key, cse))
    elif require_google:
        raise ValueError(
            "Google 검색을 사용하려면 GOOGLE_API_KEY와 GOOGLE_CSE_ID를 설정하세요."
        )
    providers.append(DuckDuckGoSearchProvider())
    return CompositeSearchProvider(tuple(providers))
