from game_scanner.register_play import *


def test_register_play():
    game_id = 161417
    r = register_play(game_id)
    assert "playid" in r.json()
