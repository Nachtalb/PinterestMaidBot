import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler

import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def download(update: Update, context: CallbackContext):
    pass


def start(update: Update, context: CallbackContext):
    update.message.reply_text('Just send me a pinterets link and I\'ll send you the content')


def main():
    updater = Updater(token=os.environ['TELEGRAM_TOKEN'], use_context=True)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
