import os
import sys
import logging
import time
import requests

import telegram

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
    format='%(asctime)s, %(levelname)s, %(message)s'
)
handler = logging.StreamHandler(stream=sys.stdout)


def send_message(bot, message):
    """Просто отправляем сообщение в чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f'{message}')


def get_api_answer(current_timestamp):
    """
    Делаем запрос к эндпоинту API.
    В случае успешного ответа - возвращаем ответ.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logging.info('Проверка запроса к API')
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != 200:
        logging.error('Ошибка запроса')
        raise requests.exceptions.RequestException(
            'Статус ответа от API не 200.', response.status_code
        )
    return response.json()


def check_response(response):
    """
    Проверяем ответ API.
    В случае корректности - возвращаем 'homeworks'.
    """
    try:
        if isinstance(response['homeworks'], list):
            return response['homeworks']
        else:
            raise Exception
    except RuntimeError as error:
        logging.error(f'Некорректный статус запроса. Ошибка: {error}')
        raise requests.exceptions.RequestException(
            'При запросе получена ошибка', error
        )


def parse_status(homework):
    """
    Извлекаем из 'homeworks' статус.
    В случае успеха, возвращаем вердикт.
    """
    try:
        homework_name = homework['homework_name']
        if 'homework_name' not in homework:
            logging.error(f'Информация о ДЗ {homework} недоступна')
            raise KeyError(
                'Информация о домашнем задании отстуствует'
            )
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        if homework_status not in HOMEWORK_STATUSES:
            raise KeyError('Статус ДЗ не был получен')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except RuntimeError as error:
        logging.error(f'Возникла ошибка {error} при запросе.')


def check_tokens():
    """Проверяем, что все токены на месте."""
    env_vars = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(env_vars)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if check_tokens() is False:
        logging.critical(
            'Не были получены все необходимые данные,'
            ' программа прекратила работу'
        )
        sys.exit()
    else:
        while True:
            try:
                response = get_api_answer(
                    current_timestamp=current_timestamp
                )
                homeworks = check_response(response)
                for homework in homeworks:
                    homework = homework.get('status')
                    message = parse_status(homework)
                    try:
                        send_message(bot, message)
                        logging.info('Сообщение было отправлено')
                    except RuntimeError as error:
                        logging.error(f'Ошибка при отправке сообщения {error}')
                        raise RuntimeError('Не удалось отправить сообщениие')
                else:
                    logging.debug('Статус не изменился')
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
