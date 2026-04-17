# -*- coding: utf-8 -*-
"""DW (Deutsche Welle) 爬虫"""
from typing import List
from datetime import datetime
import feedparser
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_article_content, get_logger


class DWCrawler(BaseCrawler):
    """DW (Deutsche Welle) 新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="dw")
        self.base_url = "https://www.dw.com/"
        # DW 的官方 RSS 源
        self.rss_feeds = [
            "https://rss.dw.com/atom/rss-en-all",
            "https://rss.dw.com/atom/rss-en-topnews",
            "https://rss.dw.com/atom/rss-en-opinion",
            "https://rss.dw.com/atom/rss-en-germany",
            "https://rss.dw.com/atom/rss-en-business",
            "https://rss.dw.com/atom/rss-en-science",
            "https://rss.dw.com/atom/rss-en-culture",
            "https://rss.dw.com/atom/rss-en-lifestyle"
        ]
    
    def fetch_news_list(self, max_count: int = 0) -> List[NewsItem]:
        """抓取 DW 新闻列表
        
        Args:
            max_count: 最大抓取条数，0 表示不限制
            
        Returns:
            NewsItem 列表
        """
        news_list = []
        logger = self._get_logger()
        
        # 使用第一个 RSS 源（全部新闻）
        rss_url = self.rss_feeds[0]
        
        try:
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries:
                if max_count > 0 and len(news_list) >= max_count:
                    break
                
                title = entry.get('title', '').strip()
                url = entry.get('link', '').strip()
                
                if not title or not url:
                    continue
                
                # 跳过非英文页面
                if '/de/' in url or '/es/' in url or '/ar/' in url or '/zh/' in url:
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
                
                # 获取摘要
                summary = entry.get('summary', '').strip()
                
                # 抓取正文内容
                content = fetch_article_content(url, logger)
                
                # 如果正文内容为空，使用摘要作为内容
                final_content = content or summary or title
                
                news_item = NewsItem(
                    title=title,
                    url=url,
                    publish_time=publish_time,
                    content=final_content,
                    source="dw"
                )
                
                if self.validate_news_item(news_item):
                    news_list.append(news_item)
                    logger.info(f"Found news: {title[:50]}...")
        
        except Exception as e:
            logger.error(f"Error parsing RSS feed {rss_url}: {e}")
        
        logger.info(f"Successfully fetched {len(news_list)} news from dw.com")
        return news_list