from flask import redirect
from loguru import logger

from game_scanner.barcode2bgg import barcode2bgg
from game_scanner.register_play import register_play


def main(request):
    request_args = request.args.to_dict()
    logger.info(request_args)
    query = request_args["query"]
    logger.info(query)
    play = "play" in request_args
    logger.info(play)
    is_redirect = "redirect" in request_args
    logger.info(is_redirect)
    #  query = "634482735077"
    #  query = "736211019233"
    #  query = "728028482775"
    #  query = "9701125875023"
    #  query = "4250231725357"
    #  query = "630509665129"
    game_id = barcode2bgg(query)
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
