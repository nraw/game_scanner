import os
from collections import Counter
from functools import lru_cache

import requests
from loguru import logger

from wishlist_scanner.errors import (NoGoogleMatchesForBarcodeError,
                                     NotBGGPageError, NotBoardgamePageError)


@lru_cache(1000)
def barcode2bgg(query, return_id=True):
    if query.isdigit():
        titles = find_titles_from_barcode(query)
        title = process_titles(titles)
    else:
        logger.warning("not really a barcode, but I'll just try to parse it")
        title = query
    logger.info(f"{title=}")
    url = get_bgg_url(title)
    is_bgg = "boardgamegeek" in url
    if not is_bgg:
        raise NotBGGPageError(value=titles[0], url=url)
    else:
        if not return_id:
            return url
        else:
            is_boardgame = "boardgame" in url
            if is_boardgame:
                game_id = url.split("/")[4]
                return game_id
            else:
                raise NotBoardgamePageError(url)


def find_titles_from_barcode(query):
    response = query_google(query)

    if "items" not in response:
        raise NoGoogleMatchesForBarcodeError(query)

    titles = get_titles(response)
    return titles


def query_google(query):
    GOOGLE_KEY = os.environ["GOOGLE_KEY"]
    GOOGLE_CX = os.environ["GOOGLE_CX"]
    real_query = requests.utils.quote(query)
    url = f"https://customsearch.googleapis.com/customsearch/v1?key={GOOGLE_KEY}&cx={GOOGLE_CX}&q={real_query}"
    res = requests.get(url)
    response = res.json()
    return response


def get_titles(response):
    titles = [item["title"].lower() for item in response["items"]]
    return titles


def process_titles(titles):
    if len(titles) == 1:
        title = titles[0]
        logger.warning(f"Only one title matched. Keeping whole title: {title}")
    else:
        other_titles = titles[1:]
        counter = Counter()
        for other_title in other_titles:
            counter += Counter(other_title.split())
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


def get_bgg_url(title):
    new_query = get_bgg_query(title)
    response = query_google(new_query)
    url = response["items"][0]["link"]
    return url


def get_bgg_query(title):
    new_query = f"boardgamegeek {title}"
    return new_query
