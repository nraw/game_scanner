from game_scanner.barcode2bgg import *


def test_barcode2bgg():
    query = "nemesis"
    bgg_id = "167355"
    res = barcode2bgg(query)
    assert bgg_id == res


def test_query_google():
    query = "nemesis boardgamegeek"
    res = query_google(query)
    assert type(res) == dict
