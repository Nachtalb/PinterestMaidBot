from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from telegram.error import BadRequest
import logging
import os
import re
import requests

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

def download_video(update: Update, data: dict):
    pinterest_id = data['id']
    videos = data['videos']['video_list']
    video_types = videos.keys()
    compatible_type = filter(None, map(lambda t: re.match('V_(\d+)P', t), video_types))
    compatible_type = max(compatible_type, key=lambda match: int(match.groups()[0])) if compatible_type else None
    compatible_type = compatible_type.string if compatible_type else None

    our_type = compatible_type or next(iter(video_types))
    video = videos[our_type]

    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('Pinterest', f'https://www.pinterest.ch/pin/{pinterest_id}'),
            InlineKeyboardButton('Source', data['rich_metadata']['url'])
        ]
    ])

    caption = '`{}`: {}'.format(pinterest_id, data['rich_metadata']['title'])
    if compatible_type:
        update.message.reply_video(video['url'], duration=video['duration'], width=video['width'],
                                   height=video['height'], thumb=video['thumbnail'],
                                   caption=caption, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=reply_markup)
    else:
        try:
            update.message.reply_document(video['url'], thumb=video['thumbnail'],
                                          caption=caption, parse_mode=ParseMode.MARKDOWN,
                                          reply_markup=reply_markup)
        except BadRequest:
            update.message.reply_markdown(f'Something went wrong, sry! `pinterest_id`')


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
