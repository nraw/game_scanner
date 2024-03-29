from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger

from game_scanner.barcode2bgg import barcode2bgg
from game_scanner.errors import NoGoogleMatchesError, NotBGGPageError

app = FastAPI()


@app.get("/scan/{barcode}")
async def scan(barcode):
    logger.info(f"{barcode=}")

    try:
        url = barcode2bgg(barcode, return_id=False)
        logger.info(f"{url=}")
    except NoGoogleMatchesError as e:
        return e.value
    except NotBGGPageError as e:
        return RedirectResponse(e.url)
    return RedirectResponse(url)


@app.get("/barcode2bgg/{barcode}")
async def call_barcode2bgg(barcode):
    logger.info(f"{barcode=}")
    bgg_id = barcode2bgg(barcode, return_id=True)
    return bgg_id
