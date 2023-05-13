import json
import os
from datetime import date, datetime

import requests


def register_play(game_id):
    #  game_id = 161417
    username = os.environ["BGG_USERNAME"]
    password = os.environ["BGG_PASS"]

    play_date = date.today().isoformat()
    play_datetime = datetime.now().isoformat()

    login_payload = {"credentials": {"username": username, "password": password}}
    headers = {"content-type": "application/json"}

    with requests.Session() as s:
        p = s.post(
            "https://boardgamegeek.com/login/api/v1",
            data=json.dumps(login_payload),
            headers=headers,
        )

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
        r = s.post(
            "https://boardgamegeek.com/geekplay.php",
            data=json.dumps(play_payload),
            headers=headers,
        )
    return r
