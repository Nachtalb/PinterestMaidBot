from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import logging
import os
import re
import requests

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

def download_video(update: Update, data: dict):
    pinterest_id = data['id']
    pass


def download_image(update: Update, data: dict):
    pinterest_id = data['id']
    image = next(iter(reversed(data.get('images', {}).values())), None)
    if not image:
        update.message.reply_markdown(f'Something went wrong, sry! `{pinterest_id}`')
        return
    image_url = image['url']
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('Pinterest', f'https://www.pinterest.ch/pin/{pinterest_id}'),
            InlineKeyboardButton('Source', data['rich_metadata']['url'])
        ]
    ])

    update.message.reply_photo(image_url,
                               caption='`{}`: {}'.format(
                                   pinterest_id,
                                   data['rich_metadata']['title']),
                               reply_markup=reply_markup,
                               parse_mode=ParseMode.MARKDOWN)

def download(update: Update, context: CallbackContext):
    results = re.findall('(pin\.it|pinterest\.[a-z]{1,3})\/(pin\/)?([0-9a-z]+)',
                         update.message.text,
                         flags=re.IGNORECASE)
    if not results:
        update.message.reply_text('No Pinterest URL found')
        return

    for pinterest_id in [group[2] for group in results]:
        response = requests.get(f'https://api.pinterest.com/v3/pidgets/pins/info/?pin_ids={pinterest_id}')
        if response.status_code != 200:
            update.message.reply_markdown(f'Something went wrong, sry! `{pinterest_id}`')
            return
        data = response.json().get('data')[0]
        if data.get('videos'):
            download_video(update, data)
        elif data.get('images'):
            download_image(update, data)

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Just send me a pinterets link and I\'ll send you the content')


def main():
    updater = Updater(token=os.environ['TELEGRAM_TOKEN'], use_context=True)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, download))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
