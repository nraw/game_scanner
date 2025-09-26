#!/usr/bin/env python3

import json
from game_scanner.db import get_collection

def dump_games_collection():
    """Dump the entire Firestore games collection to JSON"""
    collection = get_collection("games")
    games = []

    docs = collection.stream()
    for doc in docs:
        game_data = doc.to_dict()
        game_data['doc_id'] = doc.id  # Include document ID
        games.append(game_data)

    return games

if __name__ == "__main__":
    games = dump_games_collection()

    with open("games_collection.json", "w") as f:
        json.dump(games, f, indent=2, default=str)

    print(f"Dumped {len(games)} games to games_collection.json")