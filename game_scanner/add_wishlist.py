import json
import os

import requests


def add_wishlist(game_id: str):
    username = os.environ["BGG_USERNAME"]
    password = os.environ["BGG_PASS"]

    login_payload = {"credentials": {"username": username, "password": password}}
    wishlist_payload = {
        "item": {
            "collid": 0,
            #  "pp_currency": "USD",
            #  "cv_currency": "USD",
            "objecttype": "thing",
            "objectid": game_id,
            "status": {"wishlist": True},
            "wishlistpriority": 3,
            #  "acquisitiondate": null,
            #  "invdate": null,
        }
    }

    headers = {"content-type": "application/json"}

    with requests.Session() as s:
        p = s.post(
            "https://boardgamegeek.com/login/api/v1",
            data=json.dumps(login_payload),
            headers=headers,
        )
        r = s.post(
            "https://boardgamegeek.com/api/collectionitems",
            data=json.dumps(wishlist_payload),
            headers=headers,
        )
    return r
