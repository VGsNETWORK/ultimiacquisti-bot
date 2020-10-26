#!/usr/bin/env python3

from telegram import Bot
from telegram.error import Unauthorized, BadRequest
from root.util.logger import Logger
from time import sleep
import threading

""" This class is responsible of sending messages to a channel """


# ALL the methods here should use the standard telegram token from the bot
class TelegramSender:
    def __init__(self):
        self._logger = Logger()
        self._token = None
        self._bot = None

    """ initialize a bot """

    def _bot_init(self, token):
        if token == self._token:
            return
        self._bot = Bot(token)
        self._token = token

    def send_to_log(self, message):
        TOKEN = retrieve_key("TOKEN")
        LOG_CHANNEL = retrieve_key("ERROR_CHANNEL")
        self.send_message(TOKEN, LOG_CHANNEL, message)

    """ send message to a chat """

    def send_message(self, token, chat_id, message, **kwargs):
        self._bot_init(token)
        try:
            self._logger.info("sending message to chat {}".format(chat_id))
            self._bot.send_message(chat_id=chat_id, text=message, **kwargs)
        except Unauthorized:
            self._logger.error("403 Unauthorized, bot token is wrong")
        except BadRequest:
            self._logger.error("400 Bad Request")

    """ send photo to a chat """

    def send_photo(self, token, chat_id, photo, caption, **kwargs):
        self._bot_init(token)
        try:
            self._logger.info("sending photo to chat {}".format(chat_id))
            self._bot.send_photo(
                chat_id=chat_id, photo=photo, caption=caption, **kwargs
            )
        except Unauthorized:
            self._logger.error("403 Unauthorized, bot token is wrong")
        except BadRequest:
            self._logger.error("400 Bad Request")

    def send_and_delete(
        self,
        context,
        chat_id,
        text,
        reply_markup=None,
        reply_to_message_id=None,
        parse_mode="HTML",
        timeout=10,
    ):
        message = context.bot.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=True,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
            reply_markup=reply_markup,
        )
        thread = threading.Thread(
            target=self.delete_message,
            args=(context, chat_id, message.message_id, timeout),
        )
        thread.start()

    def delete_message(self, context, chat_id, message_id, timeout=0):
        sleep(timeout)
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
