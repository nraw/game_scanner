from game_scanner.barcode2bgg import *


def test_barcode2bgg():
    #  query = "634482735077"
    #  query = "736211019233"
    #  query = "728028482775"
    #  query = "9701125875023"
    #  query = "4250231725357"
    #  query = "630509665129"
    query = "nemesis"
    bgg_id = "167355"
    game_id = barcode2bgg(query)
    assert bgg_id == game_id


def test_get_bgg_url():
    query = "nemesis"
    expected_url = "https://boardgamegeek.com/boardgame/167355/nemesis"
    url = get_bgg_url(query)
    assert url == expected_url


def test_query_google():
    query = "kites a fun family game for for 2 to 6"
    url = query_google(query)
