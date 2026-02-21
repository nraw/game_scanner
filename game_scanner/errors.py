import structlog

logger = structlog.get_logger()


class NoSearchMatchesError(Exception):
    def __init__(self, value):
        self.value = value
        self.message = "lol nothing found, good luck with search query"
        logger.error(self.message, value=value)


class NotBGGPageError(Exception):
    def __init__(self, value, url):
        self.value = value
        self.url = url
        self.message = "lol how did this not return a bgg page?"
        logger.error(self.message, url=url)


class NotBoardgamePageError(Exception):
    def __init__(self, value):
        self.value = value
        self.message = "Seems the page is bgg but not a boardgame?"
        logger.error(self.message, value=value)


class SearchQuotaExceededError(Exception):
    def __init__(self, quota_message):
        self.quota_message = quota_message
        self.message = "search API quota exceeded"
        logger.error(self.message, detail=quota_message)


class SearchAPIError(Exception):
    def __init__(self, error_code, error_message):
        self.error_code = error_code
        self.error_message = error_message
        self.message = "search API error"
        logger.error(self.message, error_code=error_code, error_message=error_message)


# Backward-compatible aliases
NoGoogleMatchesError = NoSearchMatchesError
GoogleQuotaExceededError = SearchQuotaExceededError
GoogleAPIError = SearchAPIError
