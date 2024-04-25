from game_scanner.schemas import *


def test_play_request():
    game = "Spirit Island"
    play_request = PlayRequest(game=game)
    assert play_request.game == game


def test_schemas():
    example_play_request: dict = {
        "game": "Spirt Island",
        "notes": "comments go here",
        "playdate": "2024-04-19",
        #  "comments": "comments go here",
        #  "length": 60,
        #  "twitter": "false",
        #  "minutes": 60,
        #  "location": "Home",
        "objectid": "161417",
        #  "hours": 0,
        "quantity": "1",
        "date": "2024-04-19T17:13:28.642604",
        #  "action": "save",
        #  "objecttype": "thing",
        #  "ajax": 1,
        #  "players": [
        #      {
        #          "username": "nraw",
        #          "userid": 1551942,
        #          "repeat": "true",
        #          "name": "Non-BGG Friend",
        #          "selected": "false"
        #      },
        #      { "name": "Bilbo Baggins",
        #          "username": "bbag", # bgg username
        #          "userid": 1111, # bgg assigned unique user id number
        #          "selected": False, # still unsure what this does…
        #          "color": "Green", # player color or team
        #          "position": "1", # starting position
        #          "win": True,
        #          "new": True, # first play
        #          "score": "20"
        #      }
        #  ],
    }

    example_play_payload = PlayPayload(PlayRequest(**example_play_request))
    assert example_play_payload.objectid == "161417"
