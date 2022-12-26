class HTTPRequestError(Exception):
    """Исключения если response.status_code != 200."""

    def __init__(self, response):
        """Функция лоя исключения."""
        message = (
            f'Эндпоинт {response.url} недоступен. '
            f'Код ответа API: [{response.status_code}]'
        )
        super().__init__(message)


class ParseStatusError(Exception):
    """Исключения если response.status_code != 200."""

    def __init__(self, text):
        """Функция лоя исключения."""
        message = (
            f'Парсинг ответа API: {text}'
        )
        super().__init__(message)
