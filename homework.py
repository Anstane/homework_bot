import os
import sys
import logging
import time
import requests
from http import HTTPStatus

import telegram

from exceptions import (DataNotFoundError,
                        MessageError)

from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(funcName)s'
)
handler = logging.StreamHandler(stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Просто отправляем сообщение в чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f'{message}')
        logger.info('Сообщение было успешно отправлено')
    except MessageError as error:
        logger.error(f'Сообщение не было отправлено, ошибка: {error}')
        raise MessageError('Ошибка при отправке сообщения')


def get_api_answer(current_timestamp):
    """
    Делаем запрос к эндпоинту API.
    В случае успешного ответа - возвращаем ответ.
    """
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        logger.info('Проверка запроса к API')
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        logger.error('Ошибка запроса')
        raise requests.exceptions.RequestException(
            'Статус ответа от API не 200.',
            response.status_code,
            response.headers,
            response.url
        )
    try:
        return response.json()
    except DataNotFoundError as error:
        logger.error(f'Данные не были получены. Ошибка: {error}')
        raise DataNotFoundError('Проверьте передаваемые данные')


def check_response(response):
    """
    Проверяем ответ API.
    В случае корректности - возвращаем 'homeworks'.
    """
    if not isinstance(response, dict):
        raise TypeError
    else:
        try:
            homework = response.get('homeworks')
        except KeyError as error:
            logger.error(f'При получении данных возникла ошибка {error}')
    if not isinstance(homework, list):
        raise TypeError
    return homework


def parse_status(homework):
    """
    Извлекаем из 'homeworks' статус.
    В случае успеха, возвращаем вердикт.
    """
    if 'homework_name' not in homework:
        logger.error(f'Информация о ДЗ {homework} недоступна')
        raise DataNotFoundError('Информация о домашнем задании отстуствует')
    name = homework['homework_name']
    if 'status' not in homework:
        logger.error(f'Информация о ДЗ {homework} недоступна')
        raise DataNotFoundError('Информация о домашнем задании отстуствует')
    status = homework['status']
    if status not in HOMEWORK_STATUSES:
        raise DataNotFoundError('Статус ДЗ не был получен')
    verdict = HOMEWORK_STATUSES[status]
    return f'Изменился статус проверки работы "{name}". {verdict}'

def check_tokens():
    """Проверяем, что все токены на месте."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - 1000000)
    check_tokens()
    a = False
    if a:
        logger.critical(
            'Не были получены все необходимые данные,'
            ' программа прекратила работу'
        )
        sys.exit('Ошибка. Не были получены необходимые данные')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                last_homework = {
                    homework['homework_name']: homework['status']
                }
                message = parse_status(homework)
                if last_homework != homework['status']:
                    send_message(bot, message)
                    logger.info('Сообщение было отправлено')
                else:
                    logger.debug('Статус не изменился')
                    message = ('Статус не был изменён')
                    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
