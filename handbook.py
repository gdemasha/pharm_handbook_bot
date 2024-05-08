import asyncio
import logging
import os
import requests

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fake_useragent import UserAgent
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    filters,
    MessageHandler,
)
from random import choice

from exceptions import StatusCodeException


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)

try:
    loop = asyncio.get_event_loop()
except RuntimeError as e:
    if str(e).startswith('There is no current event loop in thread'):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        raise


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            'добро пожаловать!\n'
            'какое лекарство найти для тебя?'
        ),
    )


def make_request(url, headers):
    headers = {'User-Agent': ua.random}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response
        print(f'Ошибка: получен статус-код {response.status_code}')
    except StatusCodeException as e:
        print(f'Произошла ошибка: {e}')


def parsing_letter_links(response):
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')

    links = [
        link['href'] for link in soup.find(
            'div', class_='pointer'
        ).find_all('a')
    ]
    letters = [
        letter.text.split('\n') for letter in soup.find(
            'div', class_='pointer'
        ).find_all('a')
    ]

    alphabet_dict = {}
    for letter, link in zip(letters, links):
        alpha = [a.strip() for a in letter if a][0]
        alphabet_dict[f'{alpha}'] = link

    return alphabet_dict


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = make_request(url, ua)
    alphabet_dict = parsing_letter_links(response)

    message = update.message
    first_letter = message.text[0]

    for letter in alphabet_dict.keys():
        value = alphabet_dict[f'{first_letter}']

    response_for_letter = make_request(value, ua)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response_for_letter.text, 'lxml')

    name_links = [
        link['href'] for link in soup.find(
            'div', class_='tab-content'
        ).find_all('a', class_='link')
    ]

    names = [
        name.text.split('\n') for name in soup.find(
            'div', class_='tab-content'
        ).find_all('a', class_='link')
    ]

    name_dict = {}
    for name, link in zip(names, name_links):
        clean_names = [n.strip() for n in name if n][0]
        name_dict[f'{clean_names}'] = link

    if message.text in name_dict:
        drag_response = make_request(name_dict[f'{message.text}'], ua)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(drag_response.text, 'lxml')

        descriptions = [
            description.text for description in soup.find_all(
                'p', class_='OPIS_POLE',
            )
        ]
        notification = soup.find(
            'div', class_='notification__descr'
        ).text.strip()

        choices = [
            f'а, {message.text}? сейчас посмотрю...',
            f'{message.text}? помню, видела что-то такое...',
            f'момент... поищу {message.text} в справочнике',
            f'как, ты говоришь, там было? {message.text}? сейчас гляну...',
            f'мм... {message.text}? а, точно!\n',
        ]

        if descriptions:
            reply = (
                f'{choice(choices)}\n'
                f'{descriptions[1]}. Показания: {descriptions[3]}'
            )
        else:
            reply = (
                f'{choice(choices)}\n'
                f'{notification}'
            )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=reply,
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='а точно такое название?',
        )


if __name__ == '__main__':
    load_dotenv()
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    url = 'https://www.rlsnet.ru'
    ua = UserAgent()
    response = make_request(url, ua)

    answer_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), answer)
    start_handler = CommandHandler('start', start)

    application.add_handler(start_handler)
    application.add_handler(answer_handler)

    application.run_polling()
