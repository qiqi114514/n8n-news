# -*- coding: utf-8 -*-
"""爬虫模块"""

from crawlers.base import BaseCrawler, NewsItem
from crawlers.xinhua import XinhuaCrawler
from crawlers.reuters import ReutersCrawler
from crawlers.people import PeopleCrawler
from crawlers.ce import CeCrawler
from crawlers.bbc import BBCcrawler
from crawlers.apnews import APNewsCrawler
from crawlers.guardian import GuardianCrawler
from crawlers.nhk import NHKCrawler
from crawlers.dw import DWCrawler

__all__ = [
    "BaseCrawler",
    "NewsItem",
    "XinhuaCrawler",
    "ReutersCrawler",
    "PeopleCrawler",
    "CeCrawler",
    "BBCcrawler",
    "APNewsCrawler",
    "GuardianCrawler",
    "NHKCrawler",
    "DWCrawler",
]