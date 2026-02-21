import os
import threading
from collections import Counter
from datetime import datetime
from functools import lru_cache

import requests
from loguru import logger

from game_scanner.db import save_document
from game_scanner.errors import (
    NoGoogleMatchesError,
    GoogleQuotaExceededError,
    GoogleAPIError,
)
from game_scanner.search_provider import get_search_provider
from game_scanner.settings import conf


def _save_async(data, collection_name):
    """Save data asynchronously to avoid blocking the response."""
    try:
        save_document(data, collection_name=collection_name)
    except Exception as e:
        logger.error(f"Failed to save to {collection_name}: {e}")


def _save_trace(trace):
    threading.Thread(target=_save_async, args=(trace, "lookup_traces"), daemon=True).start()


@lru_cache(1000)
def barcode2bgg(query, return_id=True):
    trace = {
        "query": query,
        "provider": os.environ.get("SEARCH_PROVIDER", "brave"),
        "timestamp": datetime.utcnow(),
    }

    if query.isdigit():
        barcode_response = query_google(query)
        trace["search_results"] = barcode_response.get("items", [])

        titles = get_titles(barcode_response)
        if type(titles) == str:
            game_id = titles
            trace["shortcut"] = True
            trace["game_id"] = game_id
            trace["bgg_url"] = barcode_response["items"][0]["link"]
            _save_trace(trace)
            return game_id

        trace["shortcut"] = False
        trace["extracted_titles"] = titles
        title = process_titles(titles, query)
        trace["processed_title"] = title
    else:
        logger.warning("not really a barcode, but I'll just try to parse it")
        title = query
        trace["shortcut"] = False
        trace["search_results"] = None
        trace["extracted_titles"] = None
        trace["processed_title"] = title

    logger.info(f"{title=}")
    bgg_response = query_google(title, site="boardgamegeek.com/boardgame")
    trace["bgg_search_results"] = bgg_response.get("items", [])

    url = bgg_response["items"][0]["link"]
    trace["bgg_url"] = url

    if not return_id:
        _save_trace(trace)
        return url
    else:
        game_id = get_bgg_id_from_url(url)
        trace["game_id"] = game_id
        _save_trace(trace)
        return game_id


def find_titles_from_barcode(query):
    response = query_google(query)
    titles = get_titles(response)
    return titles


@lru_cache(1000)
def query_google(title, site=None):
    provider = get_search_provider()
    response = provider.search(title, site=site)
    return response


def get_titles(response):
    items = response.get("items")
    if items:
        link = items[0]["link"]
        if "boardgamegeek" in link and "boardgame" in link:
            bgg_id = link.split("/")[4]
            return bgg_id
    titles = [item["title"].lower() for item in response["items"]]
    return titles


def process_titles(titles, query=""):
    if len(titles) == 1:
        title = titles[0]
        logger.warning(f"Only one title matched. Keeping whole title: {title}")
    else:
        other_titles = titles[1:]
        counter = Counter()
        for other_title in other_titles:
            counter += Counter(other_title.split())
        counter = filter_counter(counter, query)
        first_title = titles[0]
        title_words = first_title.split()
        title_words = [word for word in title_words if word in counter]
        title = " ".join(title_words)
        if not title:
            title = titles[0]
            logger.warning(
                f"No common words between searches. Keeping first title: {title}"
            )
    return title


def filter_counter(counter, query):
    bad_words = conf["bad_words"]
    if query in counter:
        _ = counter.pop(query)
    for bad_word in bad_words:
        if bad_word in counter:
            _ = counter.pop(bad_word)
    return counter


def get_bgg_url(title):
    #  new_query = get_bgg_query(title)
    site = "boardgamegeek.com/boardgame"
    response = query_google(title, site=site)
    urls = [item["link"] for item in response["items"]]
    url = urls[0]
    return url


def get_bgg_query(title):
    new_query = f"boardgamegeek {title}"
    return new_query


def get_bgg_id_from_url(url):
    bgg_id = url.split("/")[4]
    return bgg_id
