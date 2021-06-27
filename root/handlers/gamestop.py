#!/usr/bin/env python3

from bs4 import BeautifulSoup as bs4
from root.model.extractor_handler import ExtractorHandler
import telegram_utils.utils.logger as logger

MATCH: str = "gamestop.it"


def load_picture(data: bs4):
    pictures = data.find("div", {"class": "mainInfo"})
    main_picture = pictures.find("a", {"class": "prodImg"})
    pictures = pictures.findAll("a", {"class": "anc"})
    pictures = [picture["href"] for picture in pictures]
    pictures.insert(0, main_picture["href"])
    return pictures


def validate(data: bs4):
    data = data.find("fieldset", {"class": "err404"})
    logger.info(data)
    return False if data else True


gamestop_handler: ExtractorHandler = ExtractorHandler(MATCH, load_picture, validate)