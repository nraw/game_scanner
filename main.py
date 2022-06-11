from wishlist_scanner.barcode2bgg import barcode2bgg


def main():
    query = "634482735077"
    query = "736211019233"
    query = "728028482775"
    query = "9701125875023"
    query = "4250231725357"
    query = "630509665129"
    game_id = barcode2bgg(query)
    print(f"www.boardgamegeek.com/boardgame/{game_id}")
