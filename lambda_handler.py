from loguru import logger

from wishlist_scanner.barcode2bgg import barcode2bgg


def lambda_handler(event, context):
    logger.info(event)
    if "queryStringParameters" in event:
        barcode = event["queryStringParameters"]["barcode"]
        redirect = event["queryStringParameters"].get("redirect", "")
    else:
        barcode = event["barcode"]
    url = barcode2bgg(barcode, return_id=False)
    if redirect:

        response = {
            "headers": {
                "Location": url,
            },
            "statusCode": 302,
            "body": "",
        }
    else:
        response = {"isBase64Encoded": False, "statusCode": 200, "body": url}

    return response
