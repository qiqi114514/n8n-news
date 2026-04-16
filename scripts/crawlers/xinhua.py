# -*- coding: utf-8 -*-
import re
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content

class XinhuaCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(name="xinhua")
        self.base_url = "http://www.news.cn/world/"

    def fetch_news_list(self, max_count: int = 10):
        news_list = []
        html = fetch_html(self.base_url, self.logger)
        if not html: return []
        soup = BeautifulSoup(html, 'lxml')
        links = soup.select('h3 a, .tit a, .list li a')
        seen_urls = set()
        for a in links:
            if len(news_list) >= max_count: break
            url, title = a.get('href', ''), a.get_text(strip=True)
            if '/202' not in url or len(title) < 10 or url in seen_urls: continue
            seen_urls.add(url)
            raw_content = fetch_article_content(url, self.logger)
            content = re.sub(r'(责任编辑|编辑|来源|校对|纠错|【纠错】|点击此处|关注新华网).*', '', raw_content, flags=re.S) if raw_content else title
            news_list.append(NewsItem(title=title, url=url, source="xinhua", content=content.strip(), publish_time=datetime.now()))
        return news_list