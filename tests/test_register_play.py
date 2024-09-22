from game_scanner.register_play import *


def test_register_play():
    game_id = 161417
    r = register_play(game_id)
    assert "playid" in r.json()


def test_get_logged_plays():
    logs_filter = {"game_ids": [167355]}
    logs_filter = {}
    plays = get_logged_plays(**logs_filter)
    assert len(plays) > 0
