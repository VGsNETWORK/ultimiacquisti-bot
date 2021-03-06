#!/usr/bin/env python3

from typing import List
from root.helper.tracked_link_helper import remove_tracked_subscriber
from root.handlers.handlers import extractor
from root.helper.user_helper import change_wishlist, get_current_wishlist_id
from root.model.wishlist import Wishlist
from root.helper.wishlist import find_default_wishlist, remove_wishlist_for_user
from mongoengine.errors import DoesNotExist
from root.model.wishlist_element import WishlistElement
import telegram_utils.utils.logger as logger
from pymongo.command_cursor import CommandCursor
from mongoengine import Q


def find_wishlist_element_by_id(_id: str):
    try:
        wish: WishlistElement = WishlistElement.objects().get(id=_id)
        return wish
    except DoesNotExist:
        return


def remove_wishlist_element_item_for_user(_id: str):
    try:
        WishlistElement.objects().get(id=_id).delete()
    except DoesNotExist:
        return


def find_containing_link(user_id: int, link: str):
    return list(WishlistElement.objects.filter(links__contains=link))[0]


def delete_all_wishlist_element_for_user(
    user_id: int, wishlist_id: str, delete_wishlist=False
):
    try:
        for element in WishlistElement.objects().filter(
            user_id=user_id, wishlist_id=wishlist_id
        ):
            for link in element.links:
                remove_tracked_subscriber(extractor.extract_code(link), user_id)
            element.delete()
        if delete_wishlist:
            remove_wishlist_for_user(wishlist_id, user_id)
            current_wishlist = get_current_wishlist_id(user_id)
            if current_wishlist == wishlist_id:
                wishlist: Wishlist = find_default_wishlist(user_id)
                if wishlist:
                    change_wishlist(user_id, str(wishlist.id))
    except Exception as e:
        logger.info(e)
        return


def count_all_wishlist_elements_for_user(user_id: int, wishlist_id: str):
    return len(
        WishlistElement.objects().filter(user_id=user_id, wishlist_id=wishlist_id)
    )


def delete_wishlist_element_photos(wish_id: str):
    wish: WishlistElement = find_wishlist_element_by_id(wish_id)
    if wish:
        wish.photos = []
        wish.save()


def count_all_wishlist_elements_for_wishlist_id(wishlist_id: str, user_id: int):
    return len(
        WishlistElement.objects().filter(wishlist_id=wishlist_id, user_id=user_id)
    )


def get_total_wishlist_element_pages_for_user(
    user_id: int, page_size: int = 5, wishlist_id=""
):
    total_products = (
        WishlistElement.objects()
        .filter(user_id=user_id, wishlist_id=wishlist_id)
        .count()
        / page_size
    )
    if int(total_products) == 0:
        return 1
    elif int(total_products) < total_products:
        return int(total_products) + 1
    else:
        return int(total_products)


def find_wishlist_element_for_user(
    user_id: int, page: int = 0, page_size: int = 5, wishlist_id=""
):
    wish: WishlistElement = (
        WishlistElement.objects()
        .filter(user_id=user_id, wishlist_id=wishlist_id)
        .order_by("-creation_date")
        .skip(page * page_size)
        .limit(page_size)
    )
    return wish


def find_next_wishlist_element(user_id: int, wishlist_element: WishlistElement):
    try:
        wishlist_id = str(wishlist_element.wishlist_id)
        wishlist_elements: List[WishlistElement] = WishlistElement.objects().filter(
            user_id=user_id,
            wishlist_id=wishlist_id,
        )

        wishlist_elements = wishlist_elements.filter(
            (Q(creation_date__lt=wishlist_element.creation_date))
        ).order_by("creation_date")
        return list(wishlist_elements)[-1]
    except Exception as e:
        logger.error(e)
        return None


def update_category_of_elements(user_id: int, old_category: str, new_category: str):
    WishlistElement.objects.filter(user_id=user_id, category=old_category).update(
        set__category=new_category
    )


def find_previous_wishlist_element(user_id: int, wishlist_element: WishlistElement):
    try:
        wishlist_id = str(wishlist_element.wishlist_id)
        wishlist_elements: List[WishlistElement] = WishlistElement.objects().filter(
            user_id=user_id,
            wishlist_id=wishlist_id,
        )
        wishlist_elements = wishlist_elements.filter(
            (Q(creation_date__gt=wishlist_element.creation_date))
        ).order_by("creation_date")
        return list(wishlist_elements)[0]
    except Exception as e:
        logger.error(e)
        return None


def add_photo(_id: str, photo: str):
    wish: WishlistElement = find_wishlist_element_by_id(_id)
    if wish:
        if len(wish.photos) < 10:
            wish.photos.insert(0, photo)
            wish.save()
        else:
            raise ValueError("max photo size reached")


def remove_photo(_id: str, photo: str):
    wish: WishlistElement = find_wishlist_element_by_id(_id)
    if wish:
        wish.photos.remove(photo)
        wish.save()


def count_all_wishlist_elements_photos(user_id: int, wishlist_id: int):
    query = [
        {
            "$match": {
                "user_id": user_id,
                "wishlist_id": wishlist_id,
                "photos": {"$ne": None},
            }
        },
        {"$group": {"_id": "$user_id", "total": {"$sum": {"$size": "$photos"}}}},
    ]
    cursor: CommandCursor = WishlistElement.objects().aggregate(query)
    total = 0
    for user in cursor:
        total = user["total"]
    return total
