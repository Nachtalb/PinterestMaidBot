from namedentities import unicode_entities as ue
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import logging
import os
import re
import requests


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def get_reply_markup(data):
    pinterest_id = data['id']
    default_buttons = []
    extra_buttons = []

    default_buttons.append(
        InlineKeyboardButton('Pinterest', f'https://www.pinterest.com/pin/{pinterest_id}')
    )

    rich_metadata = data.get('rich_metadata')
    if rich_metadata:
        site_name = rich_metadata.get('site_name', 'Source').capitalize()
        url = rich_metadata['url']
    else:
        site_name = 'Source'
        url = data.get('link')
    if url:
        default_buttons.append(InlineKeyboardButton(ue(site_name), url))

    if attr := data.get('attribution'):
        extra_buttons.append(
            InlineKeyboardButton(ue(attr['provider_name']).capitalize(), attr['url'])
        )

    if board := data.get('board'):
        extra_buttons.append(
            InlineKeyboardButton('Board', f'https://www.pinterest.com{board["url"]}')
        )

    reply_markup = [
        default_buttons,
    ]

    if extra_buttons:
        reply_markup.append(extra_buttons)
    return InlineKeyboardMarkup(reply_markup)


def get_title(data):
    return (data.get('rich_metadata') or {}).get('title') or data.get('description')


def download_video(update: Update, data: dict):
    pinterest_id = data['id']
    videos = data['videos']['video_list']
    video_types = videos.keys()
    compatible_type = filter(None, map(lambda t: re.match('V_(\d+)P', t), video_types))
    compatible_type = max(compatible_type, key=lambda match: int(match.groups()[0])) if compatible_type else None
    compatible_type = compatible_type.string if compatible_type else None

    our_type = compatible_type or next(iter(video_types))
    video = videos[our_type]

    reply_markup = get_reply_markup(data)
    caption = f'<code>{pinterest_id}</code>: {get_title(data)}'
    if compatible_type:
        update.message.reply_video(video['url'], duration=video['duration'], width=video['width'],
                                   height=video['height'], thumb=video['thumbnail'],
                                   caption=caption, parse_mode=ParseMode.HTML,
                                   reply_markup=reply_markup)
    else:
        try:
            update.message.reply_document(video['url'], thumb=video['thumbnail'],
                                          caption=caption, parse_mode=ParseMode.HTML,
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

    reply_markup = get_reply_markup(data)
    caption = f'<code>{pinterest_id}</code>: {get_title(data)}'
    update.message.reply_photo(image_url,
                               caption=caption,
                               reply_markup=reply_markup,
                               parse_mode=ParseMode.HTML)


def download_embed(update: Update, data: dict):
    pinterest_id = data['id']
    embed = data['embed']
    type = embed['src'].rsplit('.', 1)[1]
    if type not in ['gif']:
        update.message.reply_text(f'This type of media is not supported, sry! {pinterest_id}')
        return

    reply_markup = get_reply_markup(data)
    caption = f'<code>{pinterest_id}</code>: {get_title(data)}'
    if type == 'gif':
        update.message.reply_video(embed['src'],
                                   caption=caption,
                                   reply_markup=reply_markup,
                                   parse_mode=ParseMode.HTML)


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
        if data.get('embed'):
            download_embed(update, data)
        elif data.get('videos'):
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
