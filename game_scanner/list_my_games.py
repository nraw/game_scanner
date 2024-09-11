import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

import requests
from loguru import logger


def get_my_games(player_count):
    games = filter_games_by_playercount("nraw", player_count)
    return games


def get_all_games(username):
    url = f"https://boardgamegeek.com/xmlapi2/collection?username={username}&own=1"
    response = requests.get(url)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        games = []
        for item in root.findall("item"):
            game_id = item.get("objectid")
            game_name = item.find("name").text
            games.append({"bgg_id": game_id, "name": game_name})
        return games
    else:
        return []


@lru_cache(maxsize=1000)
def get_game_details(game_id):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={game_id}"
    response = requests.get(url)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        item = root.find("item")

        min_players = item.find("minplayers")
        max_players = item.find("maxplayers")

        min_players_value = (
            int(min_players.get("value")) if min_players is not None else None
        )
        max_players_value = (
            int(max_players.get("value")) if max_players is not None else None
        )

        return {"min_players": min_players_value, "max_players": max_players_value}
    else:
        return {"min_players": None, "max_players": None}


def filter_games_by_playercount(username, player_count):
    logger.info(f"Filtering games by player count for {username} and {player_count}")
    games = get_all_games(username)
    logger.info(f"Found {len(games)} games")
    if player_count is None:
        return games

    # Get details for each game in parallel
    with ThreadPoolExecutor() as executor:
        future_to_game = {
            executor.submit(get_game_details, game["bgg_id"]): game for game in games
        }
        for future in as_completed(future_to_game):
            game = future_to_game[future]
            try:
                details = future.result()
            except Exception as exc:
                logger.error(f'Game {game["bgg_id"]} generated an exception: {exc}')
            else:
                game.update(details)

    # Filter games by player count
    filtered_games = [
        game
        for game in games
        if game["min_players"] is not None
        and game["max_players"] is not None
        and game["min_players"] <= player_count <= game["max_players"]
    ]
    logger.info(f"Filtered to {len(filtered_games)} games")
    return filtered_games
