# -*- coding: utf-8 -*-
"""France 24 爬虫"""
from typing import List
from datetime import datetime
import re
import feedparser
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content, get_logger


class France24Crawler(BaseCrawler):
    """France 24 新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="france24")
        self.base_url = "https://www.france24.com/en/"
        self.rss_feeds = [
            "https://www.france24.com/en/rss",
            "https://www.france24.com/en/rss/europe",
            "https://www.france24.com/en/rss/world/",
        ]
    
    def fetch_news_list(self, max_count: int = 0) -> List[NewsItem]:
        """抓取 France 24 新闻列表
        
        Args:
            max_count: 最大抓取条数，0 表示不限制
            
        Returns:
            NewsItem 列表
        """
        news_list = []
        logger = self._get_logger()
        
        for rss_url in self.rss_feeds:
            try:
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries:
                    if max_count > 0 and len(news_list) >= max_count:
                        break
                    
                    title = entry.get('title', '').strip()
                    url = entry.get('link', '').strip()
                    
                    if not title or not url:
                        continue
                    
                    # 跳过非英语页面
                    if '/fr/' in url or '/es/' in url or '/ar/' in url:
                        continue
                    
                    # 获取发布时间
                    publish_time = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            publish_time = datetime(*entry.published_parsed[:6])
                        except Exception:
                            publish_time = datetime.now()
                    else:
                        publish_time = datetime.now()
                    
                    # 抓取正文内容
                    content = fetch_article_content(url, logger)
                    
                    news_item = NewsItem(
                        title=title,
                        url=url,
                        publish_time=publish_time,
                        content=content,
                        source="france24"
                    )
                    
                    if self.validate_news_item(news_item):
                        news_list.append(news_item)
                        logger.info(f"Found news: {title[:50]}...")
                
                if max_count > 0 and len(news_list) >= max_count:
                    break
                    
            except Exception as e:
                logger.error(f"Error parsing RSS feed {rss_url}: {e}")
        
        logger.info(f"Successfully fetched {len(news_list)} news from france24.com")
        return news_list