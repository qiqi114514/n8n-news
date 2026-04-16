# -*- coding: utf-8 -*-
"""爬虫模块"""

from crawlers.base import BaseCrawler, NewsItem
from crawlers.xinhua import XinhuaCrawler
from crawlers.reuters import ReutersCrawler
from crawlers.people import PeopleCrawler
from crawlers.cctv import CCTVcrawler
from crawlers.chinanews import ChinanewsCrawler
from crawlers.ce import CeCrawler
from crawlers.bbc import BBCcrawler
from crawlers.apnews import APNewsCrawler
from crawlers.guardian import GuardianCrawler

__all__ = [
    "BaseCrawler",
    "NewsItem",
    "XinhuaCrawler",
    "ReutersCrawler",
    "PeopleCrawler",
    "CCTVcrawler",
    "ChinanewsCrawler",
    "CeCrawler",
    "BBCcrawler",
    "APNewsCrawler",
    "GuardianCrawler",
]
