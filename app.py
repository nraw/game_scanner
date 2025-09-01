from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import RedirectResponse
from loguru import logger
from typing import Optional

from game_scanner.barcode2bgg import barcode2bgg
from game_scanner.errors import NoGoogleMatchesError, NotBGGPageError
from game_scanner.user_auth import delete_user, verify_api_key

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


@app.delete("/account")
async def delete_account(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Delete user account. Requires API key in X-API-Key header."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required in X-API-Key header")
    
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    success = delete_user(api_key)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete account")
    
    return {"message": "Account deleted successfully"}
