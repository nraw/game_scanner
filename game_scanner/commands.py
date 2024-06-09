import os

import requests
from loguru import logger

from game_scanner.add_wishlist import add_wishlist
from game_scanner.db import retrieve_play_request
from game_scanner.register_play import register_to_bgg
from game_scanner.schemas import PlayPayload


def spike_it(message_id):
    data = retrieve_play_request(message_id)
    play_payload = PlayPayload(**data).model_dump()
    r = register_to_bgg(play_payload)
    message, _ = process_register_response(r)
    update_my_board_games()
    return message


def process_register_response(r):
    res = r.json()
    relative_url = res["html"].split('"')[1]
    url = "https://boardgamegeek.com" + relative_url
    message = (
        f"SPIKED IT! You've now played it [{res['numplays']} times]({url}) (•̪ o •̪)"
    )
    return message, url


def set_it(message_id):
    data = retrieve_play_request(message_id)
    game_id = data["objectid"]
    r = add_wishlist(game_id)
    message = (
        f"You love [it](https://boardgamegeek.com/boardgame/{game_id}) now! ٩(ˊᗜˋ)و"
    )
    return message


def update_my_board_games():
    try:
        github_token = os.getenv("GH_TOKEN", "")
        headers = {
            "contentType": "application/json",
            "Accept": "application/vnd.github.v3+json",
            "Authorization": "token " + github_token,
        }
        data = {"event_type": "webhook"}
        url = "https://api.github.com/repos/nraw/my_board_games/dispatches"
        r = requests.post(url, headers=headers, json=data)
        logger.info(f"Triggered update to my_board_games: {r.status_code}")
    except:
        logger.error("Failed to update my_board_games")
