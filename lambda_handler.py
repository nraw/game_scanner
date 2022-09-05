from loguru import logger

from wishlist_scanner.barcode2bgg import barcode2bgg


def lambda_handler(event, context):
    barcode = event["barcode"]
    logger.info(event)
    url = barcode2bgg(barcode, return_id=False)
    response = dict(request=event, prediction=url)
    return response
