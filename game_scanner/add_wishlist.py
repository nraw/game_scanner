import json
import os

import requests
from loguru import logger


def add_wishlist(game_id: str, username=None, password=None):
    """Add a game to user's wishlist. Uses provided credentials or service account fallback."""
    # Use provided credentials or fall back to environment variables
    username = username or os.environ["BGG_USERNAME"]
    password = password or os.environ["BGG_PASS"]

    account_info = f" to {username}'s wishlist" if username != os.environ.get("BGG_USERNAME") else " to service account wishlist"
    logger.info(f"Adding game {game_id}{account_info}")

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

    success_msg = f"Successfully added game {game_id}{account_info}"
    logger.info(success_msg)
    return success_msg if r.status_code == 200 else f"Failed to add game {game_id}: {r.text}"
