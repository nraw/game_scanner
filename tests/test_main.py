from flask import Request

from main import *


def test_main():
    # Test with query parameter
    request = Request.from_values(
        "http://127.0.0.1:5000/?query=6416739534954&bgg_id=&bg_name=Allies+realm+of+wonder"
    )
    main(request)


def test_main():
    request = Request.from_values(
        "http://127.0.0.1:5000/?bg_name=Allies+realm+of+wonder"
    )
    main(request)
