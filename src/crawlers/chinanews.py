# -*- coding: utf-8 -*-
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content

class ChinanewsCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(name="chinanews")
        self.base_url = "https://www.chinanews.com.cn/"

    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        news_list = []
        html = fetch_html(self.base_url, self.logger)
        if not html: return news_list
        try:
            soup = BeautifulSoup(html, 'lxml')
            seen_urls = set()
            for a in soup.find_all('a', href=True):
                if len(news_list) >= max_count: break
                url, title = a['href'], a.get_text(strip=True)
                if '.shtml' not in url or len(title) < 10: continue
                if url.startswith('//'): url = 'https:' + url
                if url.startswith('/'): url = 'https://www.chinanews.com.cn' + url
                if url.count('/') < 5 or url in seen_urls: continue
                seen_urls.add(url)
                content = fetch_article_content(url, self.logger)
                news_list.append(NewsItem(title=title, url=url, publish_time=datetime.now(), content=content or title, source="chinanews"))
        except Exception as e: self.logger.error(f"Chinanews Error: {e}")
        return news_list