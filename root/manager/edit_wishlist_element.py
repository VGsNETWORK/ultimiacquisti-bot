#!/usr/bin/env python3

import re
from telegram_utils.utils.tutils import delete_if_private
from root.model.custom_category import CustomCategory
from root.helper.custom_category_helper import (
    create_category_for_user,
    find_categories_for_user,
    find_category_for_user_by_id,
)
from root.helper.wishlist import find_wishlist_by_id
from root.model.wishlist import Wishlist
from root.helper.user_helper import get_current_wishlist_id
from typing import List
from root.handlers.handlers import extractor
from root.contants.constant import CATEGORIES
from root.manager.wishlist_element import CREATE_CATEGORY, view_wishlist
from root.util.util import extract_first_link_from_message, max_length_error_format
from root.model.user import User
import telegram_utils.helper.redis as redis_helper
from telegram.chat import Chat
from telegram.message import Message
from root.contants.keyboard import (
    NEW_CUSTOM_CATEGORY_KEYBOARD,
    TOO_LONG_CUSTOM_CATEGORY_KEYBOARD,
    build_edit_wishlist_element_category_keyboard,
    build_edit_wishlist_element_desc_keyboard,
    build_edit_wishlist_element_link_keyboard,
)
from root.contants.messages import (
    ADD_LINK_TO_WISHLIST_ITEM_MESSAGE,
    CATEGORY_NAME_TOO_LONG,
    EDIT_CATEGORY_TO_WISHLIST_ITEM_MESSAGE,
    EDIT_LINK_TO_WISHLIST_ITEM_MESSAGE,
    EDIT_WISHLIST_LINK_EXISTING_PHOTOS,
    EDIT_WISHLIST_LINK_NO_PHOTOS,
    EDIT_WISHLIST_PROMPT,
    NEW_CATEGORY_MESSAGE,
    SUPPORTED_LINKS_MESSAGE,
    WISHLIST_DESCRIPTION_TOO_LONG,
    WISHLIST_HEADER,
    WISHLIST_EDIT_STEP_ONE,
    WISHLIST_EDIT_STEP_THREE,
    WISHLIST_EDIT_STEP_TWO,
    YOU_ARE_MODIFYING_THIS_ELEMENT,
)
from root.helper.wishlist_element import (
    find_wishlist_element_by_id,
    update_category_of_elements,
)
from root.model.wishlist_element import WishlistElement
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext.callbackqueryhandler import CallbackQueryHandler
from telegram.ext.conversationhandler import ConversationHandler
from telegram.ext.filters import Filters
from telegram.ext.messagehandler import MessageHandler
import telegram_utils.utils.logger as logger

EDIT_WISHLIST_TEXT, EDIT_CATEGORY, CREATE_CATEGORY = range(3)

MAX_CATEGORY_LENGTH = 15


def show_photo(wishlist_element: WishlistElement):
    return (
        f"  •  <i>{len(wishlist_element.photos)} foto</i>"
        if wishlist_element.photos
        else ""
    )


def edit_wishlist_element_item(update: Update, context: CallbackContext):
    message: Message = update.effective_message
    message_id = message.message_id
    chat: Chat = update.effective_chat
    user: User = update.effective_user
    if update.callback_query:
        if "from_link" in update.callback_query.data:
            redis_helper.save("%s_%s_user_link" % (user.id, user.id), "")
    redis_helper.save(user.id, message_id)
    logger.info("THIS IS THE CALLBACK [%s]" % update.callback_query.data)
    _id = update.callback_query.data.split("_")[-1]
    page = int(update.callback_query.data.split("_")[-2])
    wish: WishlistElement = find_wishlist_element_by_id(_id)
    index = update.callback_query.data.split("_")[-3]
    redis_helper.save("%s_%s" % (user.id, user.id), "%s_%s_%s" % (index, page, _id))
    wishlist_id = get_current_wishlist_id(user.id)
    wishlist: Wishlist = find_wishlist_by_id(wishlist_id)
    title = f"{wishlist.title.upper()}  –  "
    message = WISHLIST_HEADER % title
    append = "✏️  <i>Stai modificando questo elemento</i>"
    if not wish:
        update.callback_query.data += "_%s" % page
        view_wishlist(update, context, reset_keyboard=False)
        return
    redis_helper.save("%s_stored_wishlist_element" % user.id, wish.description)
    message += f"<b>{index}</b>  <code>{wish.description}</code>     (<i>{wish.category}</i>{show_photo(wish)})\n{append}\n\n"
    message += "\n%s%s" % (WISHLIST_EDIT_STEP_ONE, EDIT_WISHLIST_PROMPT)
    keyboard = build_edit_wishlist_element_desc_keyboard(_id, page, index)
    context.bot.edit_message_text(
        chat_id=chat.id,
        text=message,
        message_id=message_id,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    return EDIT_WISHLIST_TEXT


def edit_wishlist_element_description(
    update: Update, context: CallbackContext, from_new_category: bool = False
):
    logger.info("EDIT_WISHLIST_DESCRIPTION")
    message: Message = update.effective_message
    message_id: int = message.message_id
    chat: Chat = update.effective_chat
    user: User = update.effective_user
    if update.callback_query:
        try:
            logger.info("THESE ARE THE INFO [%s]" % update.callback_query.data)
            _id = update.callback_query.data.split("_")[-1]
            page = int(update.callback_query.data.split("_")[-2])
            index = update.callback_query.data.split("_")[-3]
        except Exception:
            info = redis_helper.retrieve(
                "edit_wishlist_element_info_%s" % user.id
            ).decode()
            logger.info("THESE ARE THE INFO [%s]" % info)
            _id = info.split("_")[-1]
            page = int(info.split("_")[-2])
            index = info.split("_")[-3]
        redis_helper.save(
            "edit_wishlist_element_info_%s" % user.id, "%s_%s_%s" % (index, page, _id)
        )
        text = ""
    else:
        context.bot.delete_message(chat_id=chat.id, message_id=message_id)
        message_id = redis_helper.retrieve(user.id).decode()
        data = redis_helper.retrieve("%s_%s" % (user.id, user.id)).decode()
        _id = data.split("_")[-1]
        page = int(data.split("_")[-2])
        index = data.split("_")[-3]
        if not from_new_category:
            text = message.text
            if not update.callback_query:
                redis_helper.save("%s_stored_wishlist_element" % user.id, text)
        else:
            text = redis_helper.retrieve(
                "%s_stored_wishlist_element" % user.id
            ).decode()
    wish: WishlistElement = find_wishlist_element_by_id(_id)
    if update.callback_query:
        if "from_category" in update.callback_query.data:
            text = redis_helper.retrieve("%s_stored_wishlist_element" % user.id)
            if text:
                text = text.decode()
            else:
                text = wish.description
    if update.callback_query:
        if "keep_current_description" in update.callback_query.data:
            text = wish.description
            text = redis_helper.save("%s_stored_wishlist_element" % user.id, text)
        if "confirm_description_mod" in update.callback_query.data:
            text = redis_helper.retrieve(
                "%s_stored_wishlist_element" % user.id
            ).decode()
        else:
            text = redis_helper.retrieve(
                "%s_stored_wishlist_element" % user.id
            ).decode()
    if len(text) > 128:
        redis_helper.save(
            "%s_stored_wishlist_element" % user.id, update.effective_message.text[:128]
        )
        user_text = max_length_error_format(update.effective_message.text, 128, 200)
        wishlist_id = get_current_wishlist_id(user.id)
        wishlist: Wishlist = find_wishlist_by_id(wishlist_id)
        title = f"{wishlist.title.upper()}  –  "
        message = (
            f"{WISHLIST_HEADER % title}<b>1.</b>  {user_text}\n"
            f"{WISHLIST_DESCRIPTION_TOO_LONG}\n{YOU_ARE_MODIFYING_THIS_ELEMENT}\n\n"
        )
        message += "\n%s%s" % (WISHLIST_EDIT_STEP_ONE, EDIT_WISHLIST_PROMPT)
        keyboard = build_edit_wishlist_element_desc_keyboard(_id, page, index, True)
        redis_helper.save(
            "%s_stored_wishlist_element" % user.id, update.effective_message.text[:128]
        )
    else:
        ask = "*" if not wish.description == text else ""
        wish.description = text
        redis_helper.save("%s_stored_wishlist_element" % user.id, text)
        wishlist_id = get_current_wishlist_id(user.id)
        wishlist: Wishlist = find_wishlist_by_id(wishlist_id)
        title = f"{wishlist.title.upper()}  –  "
        message = WISHLIST_HEADER % title
        append = "✏️  <i>Stai modificando questo elemento</i>"
        message += f"<b>{index}</b>  {ask}<b>{wish.description}</b>     (<b><i>{wish.category}</i></b>{show_photo(wish)})\n{append}\n\n"

        append = EDIT_CATEGORY_TO_WISHLIST_ITEM_MESSAGE
        message += f"\n{WISHLIST_EDIT_STEP_THREE}{append}"
        categories: List[CustomCategory] = find_categories_for_user(
            user_id=update.effective_user.id
        )
        keyboard = build_edit_wishlist_element_category_keyboard(
            _id, page, index, wish.category, categories
        )

    context.bot.edit_message_text(
        chat_id=chat.id,
        text=message,
        message_id=message_id,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    return EDIT_CATEGORY if len(text) <= 128 else EDIT_WISHLIST_TEXT


def edit_wishlist_element_link(update: Update, context: CallbackContext):
    message: Message = update.effective_message
    message_id: int = message.message_id
    chat: Chat = update.effective_chat
    user: User = update.effective_user
    if update.callback_query:
        _id = update.callback_query.data.split("_")[-1]
        page = int(update.callback_query.data.split("_")[-2])
        index = update.callback_query.data.split("_")[-3]
        link = None
    else:
        context.bot.delete_message(chat_id=chat.id, message_id=message_id)
        message_id = redis_helper.retrieve(user.id).decode()
        data = redis_helper.retrieve("%s_%s" % (user.id, user.id)).decode()
        _id = data.split("_")[-1]
        page = int(data.split("_")[-2])
        index = data.split("_")[-3]
        link = message.text if message.text else message.caption
        link = extract_first_link_from_message(update.effective_message)
        redis_helper.save("%s_%s_user_link" % (user.id, user.id), link)
        logger.info(link)
    wish: WishlistElement = find_wishlist_element_by_id(_id)
    if update.callback_query:
        if not "remove_link" in update.callback_query.data:
            if link:
                pictures = extractor.load_url(link)
                pictures = pictures[:10]
            else:
                pictures = []
        else:
            pictures = []
    else:
        pictures = extractor.load_url(link)
        pictures = pictures[:10]
    redis_helper.save("%s_%s_photos" % (user.id, user.id), str(pictures))
    logger.info("THESE ARE THE PICTURES %s" % pictures)
    if update.callback_query:
        if "remove_link" in update.callback_query.data:
            removed = "1"
            redis_helper.save("%s_removed_link" % user.id, removed)
        else:
            removed = "0"
            redis_helper.save("%s_removed_link" % user.id, removed)
    else:
        removed = "0"
        redis_helper.save("%s_removed_link" % user.id, removed)
        wish.links = link
    text = redis_helper.retrieve("%s_stored_wishlist_element" % user.id).decode()
    ask = "*" if not wish.description == text else ""
    ask = "*" if removed == "1" else ask
    ask = "*" if not update.callback_query else ask
    wish.description = text
    redis_helper.save("%s_stored_wishlist_element" % user.id, text)
    wishlist_id = get_current_wishlist_id(user.id)
    wishlist: Wishlist = find_wishlist_by_id(wishlist_id)
    title = f"{wishlist.title.upper()}  –  "
    message = WISHLIST_HEADER % title
    append = "✏️  <i>Stai modificando questo elemento</i>"
    message += f"<b>{index}</b>  {ask}<b>{wish.description}</b>     (<b><i>{wish.category}</i></b>{show_photo(wish)})\n{append}\n\n"
    message += "\n%s%s" % (
        WISHLIST_EDIT_STEP_THREE,
        EDIT_CATEGORY_TO_WISHLIST_ITEM_MESSAGE,
    )
    categories: List[CustomCategory] = find_categories_for_user(
        user_id=update.effective_user.id
    )
    context.bot.edit_message_text(
        message_id=message_id,
        chat_id=chat.id,
        text=message,
        reply_markup=build_edit_wishlist_element_category_keyboard(
            _id, page, index, wish.category, categories
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    return EDIT_CATEGORY


def edit_category(update: Update, context: CallbackContext):
    message: Message = update.effective_message
    user: User = update.effective_user
    context.bot.answer_callback_query(update.callback_query.id)
    data = update.callback_query.data
    _id = data.split("_")[-1]
    if "keep_category" in data:
        cancel_edit_wishlist_element(update, context)
        return ConversationHandler.END
    if not "custom" in data:
        category = int(data.split("_")[-4])
    else:
        info = redis_helper.retrieve("edit_wishlist_element_info_%s" % user.id).decode()
        _id = info.split("_")[-1]
        update.callback_query.data += "_%s" % info
        category: CustomCategory = find_category_for_user_by_id(
            user.id, data.split("_")[-1]
        )
        category = category.description
    wish: WishlistElement = find_wishlist_element_by_id(_id)
    text = redis_helper.retrieve("%s_stored_wishlist_element" % user.id).decode()
    removed: str = redis_helper.retrieve("%s_removed_link" % user.id).decode()
    wish.description = text
    if not "custom" in data:
        wish.category = CATEGORIES[category]
    else:
        wish.category = category
    rphotos: List[str] = redis_helper.retrieve("%s_%s_photos" % (user.id, user.id))
    rphotos = eval(rphotos.decode()) if rphotos else None
    wish.photos = rphotos if rphotos else wish.photos
    wish.save()
    cancel_edit_wishlist_element(update, context)
    return ConversationHandler.END


def cancel_edit_wishlist_element(update: Update, context: CallbackContext):
    if update.callback_query:
        page = update.callback_query.data.split("_")[-2]
        update.callback_query.data += "_%s" % page
        view_wishlist(update, context, reset_keyboard=False)
    else:
        view_wishlist(update, context, None, "0", reset_keyboard=False)
    return ConversationHandler.END


def go_back(update: Update, context: CallbackContext):
    if update.callback_query:
        if "from_category" in update.callback_query.data:
            edit_wishlist_element_item(update, context)
            return EDIT_WISHLIST_TEXT


def create_custom_category(update: Update, context: CallbackContext):
    message: Message = update.effective_message
    chat: Chat = update.effective_chat
    user: User = update.effective_user
    wishlist_id = update.callback_query.data.split("_")[-1]
    wishlist_id: str = get_current_wishlist_id(user.id)
    wishlist: Wishlist = find_wishlist_by_id(wishlist_id)
    title = f"{wishlist.title.upper()}  –  "
    text = WISHLIST_HEADER % title
    text += NEW_CATEGORY_MESSAGE % MAX_CATEGORY_LENGTH
    keyboard = NEW_CUSTOM_CATEGORY_KEYBOARD
    message_id: int = message.message_id
    redis_helper.save("new_category_message_%s" % user.id, str(message_id))
    context.bot.edit_message_text(
        message_id=message_id,
        chat_id=chat.id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    return CREATE_CATEGORY


def accept_category_modification(update: Update, context: CallbackContext):
    user: User = update.effective_user
    category_name = redis_helper.retrieve("new_category_name_%s" % user.id).decode()
    category_name = category_name[:MAX_CATEGORY_LENGTH]
    create_category_for_user(user.id, category_name)
    edit_wishlist_element_description(update, context)
    return EDIT_CATEGORY


def new_category_received(update: Update, context: CallbackContext):
    chat: Chat = update.effective_chat
    message: Message = update.effective_message
    user: User = update.effective_user
    message_id = redis_helper.retrieve("new_category_message_%s" % user.id).decode()
    category_name = message.text.lower().capitalize().split("\n")[0]
    category_name = re.sub(r"\r|\n|\s\s", "", category_name)
    if len(category_name) > MAX_CATEGORY_LENGTH:
        delete_if_private(message)
        redis_helper.save("new_category_name_%s" % user.id, category_name)
        category_name = max_length_error_format(
            category_name, MAX_CATEGORY_LENGTH, MAX_CATEGORY_LENGTH * 2
        )
        wishlist_id = get_current_wishlist_id(user.id)
        wishlist: Wishlist = find_wishlist_by_id(wishlist_id)
        title = f"{wishlist.title.upper()}  –  "
        message = (
            f"{WISHLIST_HEADER % title}{category_name}\n"
            f"{CATEGORY_NAME_TOO_LONG % MAX_CATEGORY_LENGTH}"
        )
        context.bot.edit_message_text(
            chat_id=chat.id,
            message_id=message_id,
            text=message,
            disable_web_page_preview=True,
            parse_mode="HTML",
            reply_markup=TOO_LONG_CUSTOM_CATEGORY_KEYBOARD,
        )
        return CREATE_CATEGORY
    create_category_for_user(user.id, category_name)
    edit_wishlist_element_description(update, context, True)
    return EDIT_CATEGORY


def delete_custom_category(update: Update, context: CallbackContext):
    user: User = update.effective_user
    if update.callback_query:
        data = update.callback_query.data
        _id = data.split("_")[-1]
        category: CustomCategory = find_category_for_user_by_id(user.id, _id)
        if category:
            update_category_of_elements(user.id, category.description, CATEGORIES[0])
            category.delete()
        update.callback_query.data = "skip_add_link_to_wishlist_element"
        edit_wishlist_element_description(update, context)
        return EDIT_CATEGORY


EDIT_WISHLIST_CONVERSATION = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            edit_wishlist_element_item,
            pattern="edit_wishlist_element_item",
        ),
    ],
    states={
        EDIT_WISHLIST_TEXT: [
            MessageHandler(
                Filters.text,
                edit_wishlist_element_description,
            ),
            CallbackQueryHandler(
                callback=edit_wishlist_element_description,
                pattern="keep_current_description",
            ),
            CallbackQueryHandler(
                callback=edit_wishlist_element_description,
                pattern="confirm_description_mod",
            ),
        ],
        EDIT_CATEGORY: [
            CallbackQueryHandler(
                callback=edit_category,
                pattern="edit_category",
            ),
            CallbackQueryHandler(
                callback=create_custom_category, pattern="create_new_category"
            ),
            CallbackQueryHandler(
                callback=delete_custom_category, pattern="delete_category_custom"
            ),
            CallbackQueryHandler(callback=go_back, pattern="go_back_from_category"),
        ],
        CREATE_CATEGORY: [
            CallbackQueryHandler(
                callback=edit_wishlist_element_description,
                pattern="skip_add_link_to_wishlist_element",
            ),
            CallbackQueryHandler(
                callback=accept_category_modification,
                pattern="accept_add_link_to_wishlist_element",
            ),
            MessageHandler(Filters.text, new_category_received),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(
            callback=edit_wishlist_element_link, pattern="keep_category"
        ),
        CallbackQueryHandler(
            cancel_edit_wishlist_element,
            pattern="cancel_add_to_wishlist_element",
        ),
    ],
)