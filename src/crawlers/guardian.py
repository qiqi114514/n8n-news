# -*- coding: utf-8 -*-
"""The Guardian 爬虫"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content


class GuardianCrawler(BaseCrawler):
    """The Guardian 新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="guardian")
        self.base_url = "https://www.theguardian.com"
        # 使用世界新闻页面获取最新新闻
        self.world_url = "https://www.theguardian.com/world"
    
    def fetch_news_list(self, max_count: int = 0) -> List[NewsItem]:
        """抓取 The Guardian 新闻列表"""
        news_list = []
        
        try:
            # 访问世界新闻页面
            html = fetch_html(self.world_url, self._get_logger())
            if not html:
                self._get_logger().error("Failed to fetch theguardian.com/world")
                return news_list
            
            soup = BeautifulSoup(html, 'lxml')
            seen_urls = set()
            
            # 查找所有文章链接
            for a in soup.find_all('a', href=True):
                if max_count > 0 and len(news_list) >= max_count:
                    break
                
                href = a.get('href', '')
                title = a.get_text(strip=True)
                
                # 过滤：需要是具体文章（包含日期模式），且标题长度足够
                if not title or len(title) < 20:
                    continue
                if '/liveblog/' in href or '/about' in href or '/help' in href:
                    continue
                
                # 检查是否是文章 URL（通常包含年份/月份/日期）
                import re
                if not re.search(r'/\d{4}/[a-z]{3}/\d{2}/', href):
                    continue
                
                # 处理相对路径
                if href.startswith('/'):
                    href = f"https://www.theguardian.com{href}"
                
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                # 抓取正文内容
                content = fetch_article_content(href, self._get_logger())
                
                news_item = NewsItem(
                    title=title,
                    url=href,
                    publish_time=datetime.now(),
                    content=content or title,
                    source="guardian"
                )
                
                if self.validate_news_item(news_item):
                    news_list.append(news_item)
                    self._get_logger().info(f"Found news: {title[:50]}...")
            
            self._get_logger().info(f"Successfully fetched {len(news_list)} news from theguardian.com")
        
        except Exception as e:
            self._get_logger().error(f"Error fetching theguardian.com: {e}", exc_info=True)
        
        return news_list
