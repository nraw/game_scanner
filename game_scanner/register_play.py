import json
import os
from datetime import date, datetime

import requests

from game_scanner.schemas import PlayPayload


def register_play(game_id):
    play_payload = get_play_payload(game_id)
    register_to_bgg(play_payload)


def log_play_to_bgg(**play_payload_raw):
    play_payload = PlayPayload(**play_payload_raw).dict()

    r = register_to_bgg(play_payload)
    if r.status_code != 200:
        error_message = f"Failed to log play: {r.text}"
        return error_message
    response_text = f"Successfully logged play: {play_payload}"
    return response_text


def register_to_bgg(play_payload):
    username = os.environ["BGG_USERNAME"]
    password = os.environ["BGG_PASS"]

    login_payload = {"credentials": {"username": username, "password": password}}
    headers = {"content-type": "application/json"}

    with requests.Session() as s:
        p = s.post(
            "https://boardgamegeek.com/login/api/v1",
            data=json.dumps(login_payload),
            headers=headers,
        )

        r = s.post(
            "https://boardgamegeek.com/geekplay.php",
            data=json.dumps(play_payload),
            headers=headers,
        )
    return r


def get_play_payload(game_id):
    play_date = date.today().isoformat()
    play_datetime = datetime.now().isoformat()
    play_payload = {
        "playdate": play_date,
        #  "comments": "comments go here",
        #  "length": 60,
        #  "twitter": "false",
        #  "minutes": 60,
        #  "location": "Home",
        "objectid": str(game_id),
        #  "hours": 0,
        "quantity": "1",
        "action": "save",
        "date": play_datetime,
        #  "players": [
        #      {
        #          "username": "",
        #          "userid": 0,
        #          "repeat": "true",
        #          "name": "Non-BGG Friend",
        #          "selected": "false"
        #      },
        #      {
        #          "username": "youruserid",
        #          "userid": 123456
        #          "name": "Me!",
        #          "selected": "false"
        #      }
        #  ],
        "objecttype": "thing",
        "ajax": 1,
    }
    return play_payload
