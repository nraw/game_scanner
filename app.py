from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger

from wishlist_scanner.barcode2bgg import barcode2bgg
from wishlist_scanner.errors import (NoGoogleMatchesForBarcodeError,
                                     NotBGGPageError)

app = FastAPI()


@app.get("/scan/{barcode}")
async def scan(barcode):
    logger.info(f"{barcode=}")

    try:
        url = barcode2bgg(barcode, return_id=False)
        logger.info(f"{url=}")
    except NoGoogleMatchesForBarcodeError as e:
        return e.value
    except NotBGGPageError as e:
        return RedirectResponse(e.url)
    return RedirectResponse(url)


@app.get("/barcode2bgg/{barcode}")
async def call_barcode2bgg(barcode):
    logger.info(f"{barcode=}")
    bgg_id = barcode2bgg(barcode, return_id=True)
    return bgg_id
