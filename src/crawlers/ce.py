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
        # 标题导航页通常是 td 或 li 下的 a 标签
        links = soup.select('.left_list li a, td a')
        
        seen_urls = set()
        for a in links:
            if len(news_list) >= max_count:
                break
            
            url = a.get('href', '')
            title = a.get_text(strip=True)
            
            # 补全相对路径
            if url.startswith('.'):
                url = "http://intl.ce.cn/qqss" + url.lstrip('.')
            
            # 过滤无效链接
            if 'http' not in url or len(title) < 10 or url in seen_urls:
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
