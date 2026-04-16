# -*- coding: utf-8 -*-
import re
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content

class CeCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(name="ce")
        # 锁定为你验证的国际频道
        self.base_url = "http://intl.ce.cn/qqss/index.shtml"

    def fetch_news_list(self, max_count: int = 5) -> List[NewsItem]:
        news_list = []
        html = fetch_html(self.base_url, self.logger)
        if not html: return []

        soup = BeautifulSoup(html, 'lxml')
        # 标题导航页通常是 td 或 li 下的 a 标签
        links = soup.select('.left_list li a, td a')
        
        seen_urls = set()
        for a in links:
            if len(news_list) >= max_count: break
            
            url = a.get('href', '')
            title = a.get_text(strip=True)
            
            # 补全相对路径
            if url.startswith('.'):
                url = "http://intl.ce.cn/qqss" + url.lstrip('.')
            
            if 'http' not in url or len(title) < 10 or url in seen_urls: continue
            seen_urls.add(url)

            # 抓取详情
            content = fetch_article_content(url, self.logger)
            
            news_list.append(NewsItem(
                title=title,
                url=url,
                source="ce",
                content=content or title,
                publish_time=datetime.now()
            ))
        return news_list