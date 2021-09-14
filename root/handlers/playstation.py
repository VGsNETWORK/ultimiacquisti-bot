#!/usr/bin/env python3

import re
from root.model.tracked_link import TrackedLink
from typing import List
from root.model.rule import Rule
from bs4 import BeautifulSoup as bs4
from root.model.extractor_handler import ExtractorHandler
from root.handlers.generic import extract_data
from root.util.util import de_html
import telegram_utils.utils.logger as logger
import requests
import json

BASE_URL = "https://store.playstation.com/it-it/product/"
MATCH = "store.playstation.com/it-it"
RULE = {
    "title": Rule("h1", {"class": "psw-t-title-l"}),
    "price": Rule("span", {"class": "psw-t-title-m"}),
    "platform": "Playstation",
    "store": "Playstation Store",
    "base_url": BASE_URL,
    "delivery_available": False,
    "collect_available": False,
    "bookable": False,
    "sold_out": False,
}


def get_shipment_cost(price: float, string: bool = False):
    return "" if string else 0.00


def is_bookable(data: bs4):
    bookable = data.find("span", {"class": "psw-fill-x"})
    bookable = de_html(bookable)
    return "pre-ordine" in str(bookable).lower()


def load_picture(data: bs4):
    script = data.find_all("script")[-21]
    script = de_html(script)
    try:
        script = json.loads(script)
        script = script["props"]["pageProps"]
        script = script["batarangs"]["background-image"]
        script = script["text"]
        script = de_html(script)
        script = json.loads(script)
        script = script["cache"]
        for key in script.keys():
            if "Concept" in key:
                continue
        media = script[key]["media"]
        media = [m["url"] for m in media if m["type"] == "IMAGE"]
        return media[:10]
    except KeyError:
        return []


def validate(data: bs4):
    return data.find("h2", {"class": "psw-t-title-m"}) != None


def extract_code(url: str) -> str:
    code: List[str] = re.findall(r"/product/.*", url)
    if code:
        code: str = code[0]
        return re.sub("/|product", "", code)


def extract_missing_data(product: dict, data: bs4):
    product["bookable"] = is_bookable(data)
    return product


def get_extra_info(tracked_link: TrackedLink):
    return ""


# fmt: off
playstation_handler: ExtractorHandler = \
    ExtractorHandler(BASE_URL, MATCH, load_picture, validate, \
        extract_code, extract_data, extract_missing_data, get_extra_info, get_shipment_cost, RULE)
# fmt: on