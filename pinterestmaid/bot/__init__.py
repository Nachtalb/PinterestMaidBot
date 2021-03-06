from namedentities import unicode_entities as ue
from requests_html import HTMLSession
from requests_html import HTMLSession
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import logging
import os
import re
import requests


logger = logging.getLogger('PinterestMaid')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

URL_REG = re.compile('(pin\.it|pinterest\.[a-z]{1,3})\/(pin\/)?([0-9a-z]+)', flags=re.IGNORECASE)

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
    logger.info(f'Video: {pinterest_id}')
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
            logger.info(f'Video: {pinterest_id} - Failed send with type {our_type}')
            update.message.reply_markdown(f'Something went wrong, sry! `pinterest_id`')


def download_image(update: Update, data: dict):
    pinterest_id = data['id']
    logger.info(f'Image: {pinterest_id}')
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
    logger.info(f'Embed: {pinterest_id}')
    embed = data['embed']
    type = embed['src'].rsplit('.', 1)[1]
    if type not in ['gif']:
        update.message.reply_text(f'This type of media is not supported, sry! {pinterest_id}')
        logger.info(f'Embed: {pinterest_id} - Unknown type {type}')
        return

    reply_markup = get_reply_markup(data)
    caption = f'<code>{pinterest_id}</code>: {get_title(data)}'
    if type == 'gif':
        update.message.reply_video(embed['src'],
                                   caption=caption,
                                   reply_markup=reply_markup,
                                   parse_mode=ParseMode.HTML)


def resolve_shortcut(short_id):
    logger.info(f'Resolve: {short_id}')
    session = HTMLSession()
    response = session.get(f'https://pin.it/{short_id}')
    if response.status_code == 302:
        url = response.headers['location']
    elif response.status_code == 200:
        meta_tag = response.html.find('meta[name="og:url"]')
        if not meta_tag:
            return
        url = meta_tag[0].attrs['content']
    match = next(URL_REG.finditer(url), None)
    return match.groups()[2] if match else None


def download(update: Update, context: CallbackContext):
    results = URL_REG.findall(update.message.text)
    if not results:
        if update.message.chat.type == 'private':
            update.message.reply_text('No Pinterest URL found')
        return

    ids_used = []

    for match_group in results:
        pinterest_id = match_group[2]
        logger.info(f'Incoming: {pinterest_id}')
        if match_group[0] == 'pin.it':
            actual_pinterest_id = resolve_shortcut(pinterest_id)
            if not pinterest_id:
                update.message.reply_text(f'Could not resolve short id {pinterest_id}')
                continue
            pinterest_id = actual_pinterest_id

        if pinterest_id in ids_used:
            continue
        ids_used.append(pinterest_id)

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
    logger.info(f'Start: https://t.me/{updater.bot.get_me().username}')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
