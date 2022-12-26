import logging
import os
import requests
from http import HTTPStatus
import telegram
from dotenv import load_dotenv
import time
from exceptions import HTTPRequestError, ParseStatusError
import sys

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Если все токены доступны возвращает True а в противном случаи False."""
    list_tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    check_token = True
    for token in list_tokens:
        if not token:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {token}'
            )
            check_token = False
    return check_token


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение {message}')
    except Exception as error:
        logging.error(error)


def get_api_answer(timestamp):
    """
    Функция делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передается временная метка.
    В случае успешного запроса вернет ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    params = {'from_date': timestamp}
    try:
        logging.info(f'Отправка запроса на {ENDPOINT} с параметрами {params}')
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'Запрос к {ENDPOINT} вернул ошибку: {response.status_code}'
            )
            raise HTTPRequestError(response)
        else:
            return response.json()
    except requests.RequestException as e:
        logging.error(f'При запросе к API возникает исключение: {e}')


def check_response(response):
    """Функция проверяет ответ API на соответствие документации."""
    if not response:
        error_msg = 'Содержит пустой словарь'
        logging.error(error_msg)
        raise KeyError(error_msg)

    if not isinstance(response, dict):
        error_msg = 'Имеет некоректный тип данных.'
        logging.error(error_msg)
        raise TypeError(error_msg)

    if 'homeworks' not in response:
        error_msg = 'Отсутствует ключ: homeworks'
        logging.error(error_msg)
        raise KeyError(error_msg)
    if not isinstance(response.get('homeworks'), list):
        error_msg = 'Не верный тип данных. Ответ должен содеожать список.'
        logging.error(error_msg)
        raise TypeError(error_msg)
    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        error_msg = 'Отсутствует имя проекта!'
        logging.warning(error_msg)
        raise KeyError(error_msg)

    if 'status' not in homework:
        error_msg = 'Отсутствует ключ homework_status!'
        logging.error(error_msg)
        raise ParseStatusError(error_msg)

    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)

    if homework_status not in HOMEWORK_VERDICTS:
        error_msg = 'Неизвестный статус проекта!'
        logging.error(error_msg)
        raise KeyError(error_msg)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()

    messages_sends = {
        'error': None,
    }

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug('Ответ API пуст: нет домашних работ.')
                continue
            for homework in homeworks:
                message = parse_status(homework)
                if messages_sends.get('homework_name') != message:
                    send_message(bot, message)
                    messages_sends[homework['homework_name']] = message
            timestamp = response.get('current_date')
        except Exception as error:
            error_msg = f'Сбой в работе программы: {error}'
            if messages_sends['error'] != error_msg:
                send_message(bot, error_msg)
                messages_sends['error'] = message
        else:
            messages_sends['error'] = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    # Здесь задана глобальная конфигурация для логирования
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        stream=sys.stdout
    )
    main()
