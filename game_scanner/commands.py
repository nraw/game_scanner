from game_scanner.add_wishlist import add_wishlist
from game_scanner.db import retrieve_play_request
from game_scanner.register_play import register_to_bgg
from game_scanner.schemas import PlayPayload


def spike_it(message_id):
    data = retrieve_play_request(message_id)
    play_payload = PlayPayload(**data).model_dump()
    r = register_to_bgg(play_payload)
    message, _ = process_register_response(r)
    return message


def process_register_response(r):
    res = r.json()
    relative_url = res["html"].split('"')[1]
    url = "https://boardgamegeek.com" + relative_url
    message = (
        f"SPIKED IT! You've now played it [{res['numplays']} times]({url}) (•̪ o •̪)"
    )
    return message, url


def set_it(message_id):
    data = retrieve_play_request(message_id)
    game_id = data["objectid"]
    r = add_wishlist(game_id)
    message = (
        f"You love [it](https://boardgamegeek.com/boardgame/{game_id}) now! ٩(ˊᗜˋ)و"
    )
    return message
