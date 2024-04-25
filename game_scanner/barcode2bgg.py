import os
from collections import Counter
from functools import lru_cache

import requests
from loguru import logger

from game_scanner.errors import (
    NoGoogleMatchesError,
    NotBGGPageError,
    NotBoardgamePageError,
)
from game_scanner.settings import conf


@lru_cache(1000)
def barcode2bgg(query, return_id=True):
    if query.isdigit():
        titles = find_titles_from_barcode(query)
        if type(titles) == str:
            game_id = titles
            return game_id
        title = process_titles(titles, query)
    else:
        logger.warning("not really a barcode, but I'll just try to parse it")
        title = query
    logger.info(f"{title=}")
    url = get_bgg_url(title)
    #  is_bgg = "boardgamegeek.com/boardgame" in url
    #  if not is_bgg:
    #      raise NotBGGPageError(value=title, url=url)
    #  else:
    if not return_id:
        return url
    else:
        game_id = get_bgg_id_from_url(url)
        return game_id


def find_titles_from_barcode(query):
    response = query_google(query)
    titles = get_titles(response)
    return titles


@lru_cache(1000)
def query_google(title, site=None):
    GOOGLE_KEY = os.environ["GOOGLE_KEY"]
    GOOGLE_CX = os.environ["GOOGLE_CX"]
    real_query = requests.utils.quote(title)
    url = f"https://customsearch.googleapis.com/customsearch/v1?key={GOOGLE_KEY}&cx={GOOGLE_CX}&q={real_query}"
    if site:
        url += f"&siteSearch={site}"
    res = requests.get(url)
    response = res.json()
    if "items" not in response:
        raise NoGoogleMatchesError(title)
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
