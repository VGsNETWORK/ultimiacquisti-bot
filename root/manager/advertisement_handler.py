#!/usr/bin/env python3


from root.contants.keyboard import ADS_KEYBOARDS
from telegram.update import Update
from root.contants.message_timeout import FIFTEEN_MINUTES, THIRTY_MINUTES
from telegram.message import Message
from root.contants.messages import ADS_MESSAGES
from telegram.ext.callbackcontext import CallbackContext
import random
from time import sleep
from telegram_utils.utils.tutils import send_and_delete


def send_advertisement(context: CallbackContext, group_id: int = None):
    if not group_id:
        args: dict = context.job.context
        group_id: int = args["group"]
    message = random.choice(ADS_MESSAGES)
    keyboard = ADS_KEYBOARDS[ADS_MESSAGES.index(message)]
    send_and_delete(group_id, message, reply_markup=keyboard, timeout=THIRTY_MINUTES)


def command_send_advertisement(update: Update, context: CallbackContext):
    send_advertisement(context, update.effective_chat.id)