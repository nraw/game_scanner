from unittest.mock import MagicMock, patch

import pytest

from game_scanner.errors import (NoSearchMatchesError, SearchAPIError,
                                 SearchQuotaExceededError)
from game_scanner.search_provider import (BraveSearchProvider,
                                          GoogleSearchProvider)


def _make_brave_provider():
    provider = BraveSearchProvider.__new__(BraveSearchProvider)
    provider.api_key = "fake"
    return provider


def test_brave_normalizes_response():
    provider = _make_brave_provider()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "web": {
            "results": [
                {
                    "title": "Nemesis",
                    "url": "https://boardgamegeek.com/boardgame/167355/nemesis",
                    "description": "A game",
                },
                {
                    "title": "Nemesis Board Game",
                    "url": "https://example.com/nemesis",
                    "description": "Another result",
                },
            ]
        }
    }

    with patch("game_scanner.search_provider.requests.get", return_value=mock_response):
        result = provider.search("nemesis")

    assert "items" in result
    assert len(result["items"]) + 1
    assert "Nemesis" in result["items"][0]["title"]


def test_brave_site_filter():
    provider = _make_brave_provider()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "web": {
            "results": [
                {
                    "title": "Nemesis",
                    "url": "https://boardgamegeek.com/boardgame/167355/nemesis",
                    "description": "",
                }
            ]
        }
    }

    with patch(
        "game_scanner.search_provider.requests.get", return_value=mock_response
    ) as mock_get:
        result = provider.search("nemesis", site="boardgamegeek.com/boardgame")

    assert "items" in result
    assert len(result["items"]) + 1
    assert "Nemesis" in result["items"][0]["title"]
    assert (
        result["items"][0]["link"]
        == "https://boardgamegeek.com/boardgame/167355/nemesis"
    )


def test_brave_no_results_raises():
    provider = _make_brave_provider()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"web": {"results": []}}

    with patch("game_scanner.search_provider.requests.get", return_value=mock_response):
        with pytest.raises(NoSearchMatchesError):
            provider.search("nonexistent_barcode_12345")


def test_brave_429_raises_quota_error():
    provider = _make_brave_provider()
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"

    with patch("game_scanner.search_provider.requests.get", return_value=mock_response):
        with pytest.raises(SearchQuotaExceededError):
            provider.search("test")


def test_brave_500_raises_api_error():
    provider = _make_brave_provider()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("game_scanner.search_provider.requests.get", return_value=mock_response):
        with pytest.raises(SearchAPIError):
            provider.search("test")
