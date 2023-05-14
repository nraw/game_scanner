from game_scanner.barcode2bgg import *


def test_barcode2bgg():
    query = "nemesis"
    bgg_id = "167355"
    #  query = "634482735077"
    #  query = "736211019233"
    #  query = "728028482775"
    #  query = "9701125875023"
    #  query = "4250231725357"
    #  query = "630509665129"
    game_id = barcode2bgg(query)
    assert bgg_id == game_id


def test_query_google():
    query = "nemesis boardgamegeek"
    res = query_google(query)
    assert type(res) == dict
