from game_scanner.barcode2bgg import get_bgg_id_from_url, get_bgg_url


def get_extra_info(play_request):
    objectid = get_bgg_id(play_request.game)
    url = "https://boardgamegeek.com/boardgame/" + objectid

    extra_info = dict(objectid=objectid, url=url)
    return extra_info


def play_request_to_md(data):
    for key, val in data.items():
        if isinstance(val, list):
            data[key] = ", ".join(val)
    pretty_message = ""
    for key, value in data.items():
        if key == "url":
            continue
        elif key == "objectid" and "url" in data:
            pretty_message += f"*{key}*: [{value}]({data['url']})\n"
        else:
            pretty_message += f"*{key}*: {value}\n"
    return pretty_message


def md_to_play_request(input_str):
    data = {}
    pairs = input_str.split("\n")
    for pair in pairs:
        if pair:
            key, value = pair.split(": ")
            key = key.replace("*", "")
            if "," in value:
                value = [item.strip() for item in value.split(",")]
            data[key] = value
    return data


def get_bgg_id(game):
    url = get_bgg_url(game)
    bgg_id = get_bgg_id_from_url(url)
    return bgg_id
