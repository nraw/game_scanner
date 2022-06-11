from loguru import logger


class NoGoogleMatchesForBarcodeError(Exception):
    def __init__(self, value):
        self.value = value
        self.message = "lol nothing found, good luck dude"
        logger.error(self.message)


class NotBGGPageError(Exception):
    def __init__(self, value, url):
        self.value = value
        self.url = url
        self.message = "lol how did this not return a bgg page?"
        logger.error(self.message)


class NotBoardgamePageError(Exception):
    def __init__(self, value):
        self.value = value
        self.message = "Seems the page is bgg but not a boardgame?"
        logger.error(self.message)
