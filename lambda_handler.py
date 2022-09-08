from loguru import logger

from wishlist_scanner.barcode2bgg import barcode2bgg


def lambda_handler(event, context):
    logger.info(event)
    if "queryStringParameters" in event:
        barcode = event["queryStringParameters"]["barcode"]
    else:
        barcode = event["barcode"]
    url = barcode2bgg(barcode, return_id=False)
    response = {"isBase64Encoded": False, "statusCode": 200, "body": url}
    #  response = dict(request=event, prediction=url)
    return response
