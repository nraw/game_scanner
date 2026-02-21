from loguru import logger


class NoSearchMatchesError(Exception):
    def __init__(self, value):
        self.value = value
        self.message = "lol nothing found, good luck with search query"
        logger.error(f"{self.message}: {value}")


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


class SearchQuotaExceededError(Exception):
    def __init__(self, quota_message):
        self.quota_message = quota_message
        self.message = f"Search API quota exceeded: {quota_message}"
        logger.error(self.message)


class SearchAPIError(Exception):
    def __init__(self, error_code, error_message):
        self.error_code = error_code
        self.error_message = error_message
        self.message = f"Search API error {error_code}: {error_message}"
        logger.error(self.message)


# Backward-compatible aliases
NoGoogleMatchesError = NoSearchMatchesError
GoogleQuotaExceededError = SearchQuotaExceededError
GoogleAPIError = SearchAPIError
