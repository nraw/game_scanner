from game_scanner.play_payload_management import *
from game_scanner.schemas import PlayRequest


def test_play_request_to_md():
    game = "Spirit Island"
    play_request = PlayRequest(game=game)
    play_request_md = play_request_to_md(play_request.model_dump())
    assert "*game*: Spirit Island\n" in play_request_md


def test_md_to_play_request():
    game = "Spirit Island"
    play_request = PlayRequest(game=game)
    play_request_md = play_request_to_md(play_request.model_dump())
    play_request_from_md = md_to_play_request(play_request_md)
    assert play_request_from_md["game"] == game
