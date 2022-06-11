import os
from collections import Counter
from functools import lru_cache

import requests


@lru_cache(1000)
def barcode2bgg(query):
    response = query_google(query)

    if "items" not in response:
        print("lol nothing found, good luck dude")
        return query
    titles = get_titles(response)
    title = process_titles(titles)

    new_query = f"bgg {title}"
    response = query_google(new_query)
    url = response["items"][0]["link"]
    is_boardgamegeek = "boardgamegeek" in url
    if not is_boardgamegeek:
        print("problem")
        return titles[0]
    else:
        game_id = url.split("/")[4]
        return game_id


def query_google(query):
    GOOGLE_KEY = os.environ["GOOGLE_KEY"]
    GOOGLE_CX = os.environ["GOOGLE_CX"]
    real_query = requests.utils.quote(query)
    url = f"https://customsearch.googleapis.com/customsearch/v1?key={GOOGLE_KEY}&cx={GOOGLE_CX}&q={real_query}"
    res = requests.get(url)
    response = res.json()
    return response


def get_titles(response):
    titles = [item["title"] for item in response["items"]]
    return titles


def process_titles(titles):
    other_titles = titles[1:]
    counter = Counter()
    for other_title in other_titles:
        counter += Counter(other_title.split())
    first_title = titles[0]
    title_words = first_title.split()
    title_words = [word for word in title_words if word in counter]
    title = " ".join(title_words)
    return title
