"""Interpret failed car-detail responses consistently across the collector."""


def is_sold_response(returncode, message):
    return returncode == 99999 or "下架" in str(message or "")


class FailedResponses:
    def __init__(self, logger):
        self.logger = logger
        self.logged = 0

    def log(self, listing_id, returncode, message):
        if self.logged < 3:
            text = str(message)[:150] if message is not None else None
            self.logger.warning("{}: ошибка API, код {!r}, сообщение {!r}",
                                listing_id, returncode, text)
            self.logged += 1
