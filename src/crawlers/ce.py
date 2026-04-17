# -*- coding: utf-8 -*-
"""中国经济网爬虫"""
import re
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content


class CeCrawler(BaseCrawler):
    """中国经济网新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="ce")
        # 锁定国际频道
        self.base_url = "http://intl.ce.cn/qqss/index.shtml"
    
    def fetch_news_list(self, max_count: int = 5) -> List[NewsItem]:
        """抓取中国经济网新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        # 查找包含日期模式的新闻链接（如 /202604/t20260417_xxx.shtml）
        all_links = soup.find_all('a', href=True)
        
        seen_urls = set()
        for a in all_links:
            if len(news_list) >= max_count:
                break
            
            url = a.get('href', '')
            title = a.get_text(strip=True)
            
            # 补全相对路径
            if url.startswith('./'):
                url = "http://intl.ce.cn/qqss" + url[1:]
            
            # 过滤：需要包含日期模式且标题长度足够
            if ('t2026' not in url and '/2026' not in url) or len(title) < 10 or url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 抓取详情
            content = fetch_article_content(url, self._get_logger())
            
            news_list.append(NewsItem(
                title=title,
                url=url,
                source="ce",
                content=content or title,
                publish_time=datetime.now()
            ))
        
        return news_list
