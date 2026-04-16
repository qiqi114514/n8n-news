# -*- coding: utf-8 -*-
"""中国新闻网爬虫"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content


class ChinanewsCrawler(BaseCrawler):
    """中国新闻网新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="chinanews")
        self.base_url = "https://www.chinanews.com.cn/"
    
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取中国新闻网新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        if not html:
            return news_list
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            seen_urls = set()
            
            for a in soup.find_all('a', href=True):
                if len(news_list) >= max_count:
                    break
                
                url = a['href']
                title = a.get_text(strip=True)
                
                # 过滤无效链接
                if '.shtml' not in url or len(title) < 10:
                    continue
                
                # 处理协议相对 URL
                if url.startswith('//'):
                    url = 'https:' + url
                if url.startswith('/'):
                    url = 'https://www.chinanews.com.cn' + url
                
                # 验证 URL 格式
                if url.count('/') < 5 or url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # 抓取正文内容
                content = fetch_article_content(url, self._get_logger())
                
                news_list.append(NewsItem(
                    title=title,
                    url=url,
                    publish_time=datetime.now(),
                    content=content or title,
                    source="chinanews"
                ))
        
        except Exception as e:
            self._get_logger().error(f"Chinanews Error: {e}")
        
        return news_list
