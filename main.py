from flask import redirect, render_template
from loguru import logger

from game_scanner.barcode2bgg import barcode2bgg
from game_scanner.db import retrieve_document
from game_scanner.register_play import register_play
from game_scanner.save_bgg_id import save_bgg_id


def main(request):
    request_args = request.args.to_dict()
    logger.info(request_args)
    query = request_args.get("query")
    logger.info(query)
    play = "play" in request_args
    logger.info(play)
    is_redirect = "redirect" in request_args
    logger.info(is_redirect)
    bgg_id = request_args.get("bgg_id")
    logger.info(bgg_id)
    bg_name = request_args.get("bg_name")
    logger.info(bg_name)

    try:
        game_id = get_game_id(bgg_id, bg_name, query)
    except Exception:
        return render_template("mapper.html", query=query)
    was_automatic = not ((bgg_id or bg_name) and query)
    save_bgg_id(query, game_id, extra={"auto": was_automatic})
    url = f"https://www.boardgamegeek.com/boardgame/{game_id}"
    logger.info(url)
    if play:
        logger.info("Registering play")
        r = register_play(game_id)
        logger.info(r)
    if is_redirect:
        logger.info("Redirecting")
        return redirect(url)
    return game_id


def get_game_id(bgg_id, bg_name, query):
    if bgg_id:
        game_id = bgg_id
        return game_id
    if bg_name:
        game_id = barcode2bgg(bg_name)
        return game_id
    saved_bgg_id = retrieve_document(query)
    if saved_bgg_id:
        game_id = saved_bgg_id
        return game_id
    game_id = barcode2bgg(query)
    return game_id
