import json
import os

import requests
import structlog

logger = structlog.get_logger()


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

    logger.info("adding game to collection", game_id=game_id, collection_type=collection_type, username=username)

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

    success_msg = f"Successfully added game {game_id} to {username}'s {collection_type}"
    logger.info("added game to collection", game_id=game_id, collection_type=collection_type, username=username)
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
