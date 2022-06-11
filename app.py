from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from wishlist_scanner.barcode2bgg import barcode2bgg

app = FastAPI()


@app.get("/scan/{barcode}")
async def scan(barcode):
    print(barcode)
    bgg_id = barcode2bgg(barcode)
    url = f"https://www.boardgamegeek.com/boardgame/{bgg_id}"
    print(url)
    return RedirectResponse(url)
