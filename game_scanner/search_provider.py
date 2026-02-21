import os
from abc import ABC, abstractmethod

import requests
import structlog

logger = structlog.get_logger()

from game_scanner.errors import (
    NoSearchMatchesError,
    SearchQuotaExceededError,
    SearchAPIError,
)


class SearchProvider(ABC):
    """Base class for web search providers."""

    @abstractmethod
    def search(self, query: str, site: str | None = None) -> dict:
        """
        Execute a web search.

        Args:
            query: The search query string.
            site: Optional domain to restrict results to.

        Returns:
            dict with key "items", a list of dicts each having "title" and "link".

        Raises:
            NoSearchMatchesError: No results found.
            SearchQuotaExceededError: Rate/quota limit hit.
            SearchAPIError: Other API error.
        """
        ...


class BraveSearchProvider(SearchProvider):
    """Brave Web Search API provider."""

    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self):
        self.api_key = os.environ["BRAVE_API_KEY"]

    def search(self, query: str, site: str | None = None) -> dict:
        q = f"{query} site:{site}" if site else query

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        res = requests.get(self.BASE_URL, params={"q": q}, headers=headers)

        if res.status_code == 429:
            raise SearchQuotaExceededError("Brave API rate limit exceeded")
        if res.status_code != 200:
            raise SearchAPIError(res.status_code, res.text)

        data = res.json()
        results = data.get("web", {}).get("results", [])

        if not results:
            raise NoSearchMatchesError(query)

        items = [{"title": r["title"], "link": r["url"]} for r in results]
        return {"items": items}


class GoogleSearchProvider(SearchProvider):
    """Google Custom Search API provider (legacy)."""

    def __init__(self):
        self.api_key = os.environ["GOOGLE_KEY"]
        self.cx = os.environ["GOOGLE_CX"]

    def search(self, query: str, site: str | None = None) -> dict:
        real_query = requests.utils.quote(query)
        url = f"https://customsearch.googleapis.com/customsearch/v1?key={self.api_key}&cx={self.cx}&q={real_query}"
        if site:
            url += f"&siteSearch={site}"

        res = requests.get(url)
        response = res.json()

        if "error" in response:
            error_info = response["error"]
            if error_info.get("code") == 429:
                raise SearchQuotaExceededError(
                    error_info.get("message", "Rate limit exceeded")
                )
            raise SearchAPIError(error_info.get("code"), error_info.get("message"))

        if "items" not in response:
            raise NoSearchMatchesError(query)

        return response


_PROVIDERS = {
    "brave": BraveSearchProvider,
    "google": GoogleSearchProvider,
}

_provider_instance: SearchProvider | None = None


def get_search_provider() -> SearchProvider:
    """Return the configured search provider singleton.

    Reads SEARCH_PROVIDER env var (default: "brave").
    """
    global _provider_instance
    if _provider_instance is None:
        name = os.environ.get("SEARCH_PROVIDER", "brave").lower()
        provider_cls = _PROVIDERS.get(name)
        if provider_cls is None:
            raise ValueError(
                f"Unknown search provider '{name}'. Available: {list(_PROVIDERS.keys())}"
            )
        _provider_instance = provider_cls()
        logger.info("initialized search provider", provider=name)
    return _provider_instance
