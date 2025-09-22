import json
import os

import requests
from loguru import logger


def add_to_collection(game_id: str, status_config: dict, collection_type: str, username=None, password=None):
    """
    Add a game to user's BGG collection with specified status.

    Args:
        game_id: BGG game ID
        status_config: Dictionary containing status settings (e.g., {"wishlist": True} or {"own": True})
        collection_type: Human-readable collection type for logging (e.g., "wishlist", "owned collection")
        username: BGG username (optional, falls back to service account)
        password: BGG password (optional, falls back to service account)
    """
    # Use provided credentials or fall back to environment variables
    username = username or os.environ["BGG_USERNAME"]
    password = password or os.environ["BGG_PASS"]

    account_info = f" to {username}'s {collection_type}" if username != os.environ.get("BGG_USERNAME") else f" to service account {collection_type}"
    logger.info(f"Adding game {game_id}{account_info}")

    login_payload = {"credentials": {"username": username, "password": password}}

    # Base collection item payload
    collection_payload = {
        "item": {
            "collid": 0,
            "objecttype": "thing",
            "objectid": game_id,
            "status": status_config,
        }
    }

    # Add wishlist priority if this is a wishlist item
    if status_config.get("wishlist"):
        collection_payload["item"]["wishlistpriority"] = 3

    headers = {"content-type": "application/json"}

    with requests.Session() as s:
        login_response = s.post(
            "https://boardgamegeek.com/login/api/v1",
            data=json.dumps(login_payload),
            headers=headers,
        )

        collection_response = s.post(
            "https://boardgamegeek.com/api/collectionitems",
            data=json.dumps(collection_payload),
            headers=headers,
        )

    success_msg = f"Successfully added game {game_id}{account_info}"
    logger.info(success_msg)
    return success_msg if collection_response.status_code == 200 else f"Failed to add game {game_id}: {collection_response.text}"


def add_wishlist(game_id: str, username=None, password=None):
    """Add a game to user's wishlist. Uses provided credentials or service account fallback."""
    return add_to_collection(
        game_id=game_id,
        status_config={"wishlist": True},
        collection_type="wishlist",
        username=username,
        password=password
    )


def add_owned(game_id: str, username=None, password=None):
    """Add a game to user's owned collection. Uses provided credentials or service account fallback."""
    return add_to_collection(
        game_id=game_id,
        status_config={"own": True},
        collection_type="owned collection",
        username=username,
        password=password
    )
