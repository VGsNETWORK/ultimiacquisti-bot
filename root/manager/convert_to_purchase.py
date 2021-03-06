#!/usr/bin/env python3


from root.helper.user_helper import get_current_wishlist_id
from root.helper.wishlist import find_wishlist_by_id
from root.model.wishlist import Wishlist
from telegram.error import BadRequest
from root.contants.messages import (
    ASK_FOR_CONVERT_WISHLIST,
    VGS_GROUPS_PRIMARY_LINK,
    WISHLIST_HEADER,
)
from typing import List

from telegram.files.inputmedia import InputMediaPhoto
from root.model.user import User
from root.manager.wishlist_element import view_wishlist
from urllib.parse import quote
from root.helper.wishlist_element import find_wishlist_element_by_id
from root.model.wishlist_element import WishlistElement
from root.util.util import create_button
from telegram import Update
from telegram.chat import Chat
from telegram.ext import CallbackContext
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.message import Message
import telegram_utils.helper.redis as redis_helper


MAX_LINK_LENGTH = 27


def show_photos_and_links(wishlist_element: WishlistElement):
    if not wishlist_element.links:
        return (
            f"  •  <i>{len(wishlist_element.photos)} foto</i>"
            if wishlist_element.photos
            else ""
        )
    else:
        if wishlist_element.photos:
            return f"  •  <i>{len(wishlist_element.photos)} foto</i>  •  <i>{len(wishlist_element.links)} link</i>"
        else:
            return f"  •  <i>{len(wishlist_element.links)} link</i>"


def ask_confirm_deletion(update: Update, context: CallbackContext):
    message: Message = update.effective_message
    chat: Chat = update.effective_chat
    context.bot.answer_callback_query(update.callback_query.id)
    user: User = update.effective_user
    message_id = message.message_id
    _id = update.callback_query.data.split("_")[-1]
    page = int(update.callback_query.data.split("_")[-2])
    index = update.callback_query.data.split("_")[-3]
    append = "🔄  <i>Stai per convertire questo elemento in un acquisto</i>"
    wish: WishlistElement = find_wishlist_element_by_id(_id)
    if wish.photos:
        text = ""
        context.bot.delete_message(chat_id=chat.id, message_id=message_id)
    else:
        wishlist_id = get_current_wishlist_id(user.id)
        wishlist: Wishlist = find_wishlist_by_id(wishlist_id)
        title = f"{wishlist.title.upper()}  –  "
        text = WISHLIST_HEADER % title
    if not wish:
        update.callback_query.data += "_%s" % page
        view_wishlist(update, context, reset_keyboard=False)
        return
    text += f"<b>{index}</b>  <b>{wish.description}</b>     (<i>{wish.category}</i>{show_photos_and_links(wish)})\n{append}\n\n"
    if not wish.photos:
        text += (
            "<b>Vuoi continuare?</b>\n<i>Questa azione è irreversibile"
            " e <u><b>cancellerà l'elemento</b></u> dalla lista dei desideri.</i>"
        )
    else:
        text += ASK_FOR_CONVERT_WISHLIST
    keyboard = InlineKeyboardMarkup(
        [
            [
                create_button(
                    "🤍  🔄  🛍",
                    f"delete_wish_and_create_purchase_link_{page}_{_id}",
                    f"delete_wish_and_create_purchase_link_{page}_{_id}",
                ),
            ],
            [
                create_button(
                    "❌  Annulla",
                    f"view_wishlist_element_noreset_convert_{page}",
                    f"view_wishlist_element_noreset_convert_{page}",
                ),
            ],
        ]
    )
    photos: List = wish.photos
    photos = [InputMediaPhoto(media=photo) for photo in photos]
    if len(photos) > 1:
        message: List[Message] = context.bot.send_media_group(
            chat_id=chat.id, media=photos
        )
        message = [m.message_id for m in message]
    elif len(photos) == 1:
        message: Message = context.bot.send_photo(
            chat_id=chat.id, photo=photos[0].media
        )
        message = [message.message_id]
    else:
        mesasge = []
    redis_helper.save("%s_photos_message" % user.id, str(message))
    if wish.photos:
        message: Message = context.bot.send_message(
            chat_id=chat.id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
            parse_mode="HTML",
        )
    else:
        message: Message = context.bot.edit_message_text(
            chat_id=chat.id,
            message_id=message_id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
            parse_mode="HTML",
        )
    message_id: int = message.message_id
    redis_helper.save("%s_redis_message" % user.id, message_id)


def wishlist_element_confirm_convertion(update: Update, context: CallbackContext):
    message: Message = update.effective_message
    chat: Chat = update.effective_chat
    message_id = message.message_id
    context.bot.answer_callback_query(update.callback_query.id)
    user: User = update.effective_user
    _id = update.callback_query.data.split("_")[-1]
    wish: WishlistElement = find_wishlist_element_by_id(_id)
    page = int(update.callback_query.data.split("_")[-2])
    wish_description = "<b>%s</b>" % wish.description
    url = (
        "https://t.me/share/url?url=%23ultimiacquisti%20%3C"
        f"prezzo%3E%20%3CDD%2FMM%2FYY%28YY%29%3E%0A%0A%25{quote(wish.description)}%25"
    )
    if wish.links:
        if len(wish.links) == 1:
            wish_description = '<a href="%s">%s</a>' % (wish.links[0], wish_description)
        url += "%0A"
        for link in wish.links:
            if len(link) > MAX_LINK_LENGTH:
                link = '<a href="%s">%s...</a>' % (
                    link,
                    link[:MAX_LINK_LENGTH],
                )
            url += f"%0A➜%20%20{quote(link)}"
    url += "%0A%0A%0A__Importato%20da%20lista%20dei%20desideri.__"
    wish.delete()
    keyboard = InlineKeyboardMarkup(
        [
            [
                create_button(
                    "🛍  Registra l'acquisto",
                    f"convert_and_do_a_barrel_roll",
                    f"convert_and_do_a_barrel_roll",
                    url,
                ),
            ],
            [
                create_button(
                    "↩️  Torna indietro",
                    f"view_wishlist_element_{page}",
                    f"view_wishlist_element_{page}",
                ),
            ],
        ]
    )
    wishlist_id = get_current_wishlist_id(user.id)
    wishlist: Wishlist = find_wishlist_by_id(wishlist_id)
    title = f"{wishlist.title.upper()}  –  "
    text = WISHLIST_HEADER % title
    message = WISHLIST_HEADER % title
    message += (
        "😃  Link di acquisto per <b>%s</b> creato!\n\nPuoi registrare il tuo nuovo acquisto"
        f' premendo il tasto sottostante e selezionando un <a href="{VGS_GROUPS_PRIMARY_LINK}"><b><u>gruppo in cui sono presente</u></b></a>'
        % wish_description
    )
    messages = redis_helper.retrieve("%s_photos_message" % user.id).decode()
    if messages:
        messages = eval(messages)
    else:
        messages = []
    for message_id in messages:
        try:
            context.bot.delete_message(chat_id=chat.id, message_id=message_id)
        except BadRequest:
            pass
    message_id = redis_helper.retrieve("%s_redis_message" % user.id).decode()
    context.bot.edit_message_text(
        chat_id=chat.id,
        message_id=message_id,
        text=message,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode="HTML",
    )