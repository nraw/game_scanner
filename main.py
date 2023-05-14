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

    if bgg_id:
        game_id = bgg_id
    else:
        saved_bgg_id = retrieve_document(query)
        if saved_bgg_id:
            game_id = saved_bgg_id
        else:
            try:
                game_id = barcode2bgg(query)
            except Exception:
                return render_template("mapper.html", query=query)
            save_bgg_id(query, game_id, extra={"auto": True})
    if bgg_id and query:
        save_bgg_id(query, bgg_id, extra={"auto": False})
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
