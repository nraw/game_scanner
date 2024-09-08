import json
import os
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Optional

import requests

from game_scanner.schemas import PlayPayload


def log_play_to_bgg(**play_payload_raw):
    play_payload = PlayPayload(**play_payload_raw).model_dump()

    r = register_to_bgg(play_payload)
    if r.status_code != 200:
        error_message = f"Failed to log play: {r.text}"
        return error_message
    response_text = f"Successfully logged play: {play_payload}"
    return response_text


def register_play(game_id):
    play_payload = get_play_payload(game_id)
    register_to_bgg(play_payload)


def list_played_games(**logs_filter):
    plays = get_logged_plays(**logs_filter)
    return plays


def register_to_bgg(play_payload):
    username = os.environ["BGG_USERNAME"]
    password = os.environ["BGG_PASS"]

    login_payload = {"credentials": {"username": username, "password": password}}
    headers = {"content-type": "application/json"}

    with requests.Session() as s:
        _ = s.post(
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


def get_logged_plays(last_n: Optional[int] = None, since: Optional[str] = None):
    # User name
    username = os.environ["BGG_USERNAME"]

    # REST API URL to fetch all plays of a user
    url = f"https://www.boardgamegeek.com/xmlapi2/plays?username={username}"

    # Sending HTTP request
    response = requests.get(url)

    # raising exception in case of bad requests
    response.raise_for_status()

    # Creating ElementTree object
    root = ET.fromstring(response.content)
    plays = []

    # Parse the XML and find the plays
    for i, play in enumerate(root.findall("play")):
        if last_n and i >= last_n:
            break
        if since is not None:
            play_date = play.get("date", "")
            if play_date < since:
                break
        play_id = play.get("id")
        date = play.get("date")
        game_item = play.find("item")
        if game_item:
            game = game_item.get("name")
            game_id = game_item.get("objectid")  # added line to get game_ids
        else:
            raise ValueError
        comments = play.find("comments")
        comment = comments.text if comments else None
        play_info = dict(
            play_id=play_id, date=date, game=game, game_id=game_id, comment=comment
        )
        plays.append(play_info)
    return plays


def delete_logged_play(play_id):

    username = os.environ["BGG_USERNAME"]
    password = os.environ["BGG_PASS"]

    login_payload = {"credentials": {"username": username, "password": password}}
    delete_play_payload = get_delete_play_payload(play_id)
    headers = {"content-type": "application/json"}

    with requests.Session() as s:
        _ = s.post(
            "https://boardgamegeek.com/login/api/v1",
            data=json.dumps(login_payload),
            headers=headers,
        )

        r = s.post(
            "https://boardgamegeek.com/geekplay.php",
            data=json.dumps(delete_play_payload),
            headers=headers,
        )
    return r.text


def get_delete_play_payload(play_id):
    delete_play_payload = {
        "playid": play_id,
        "ajax": 1,
        "finalize": 1,
        "action": "delete",
    }
    return delete_play_payload
