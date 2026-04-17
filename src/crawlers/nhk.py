# -*- coding: utf-8 -*-
"""NHK World 爬虫"""
from typing import List, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup, Tag
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content


class NHKCrawler(BaseCrawler):
    """NHK World 新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="nhk")
        self.base_url = "https://www3.nhk.or.jp/nhkworld/en/news/list/"
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        # 尝试多种格式
        formats = [
            "%B %d, %Y",  # April 16, 2026
            "%b %d, %Y",  # Apr 16, 2026
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取 NHK World 新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        
        if not html:
            self._get_logger().error("Failed to fetch nhk.or.jp/nhkworld/en/news/list/")
            return news_list
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 使用正确的选择器获取文章列表
            articles = soup.select('.c-articleList .c-article')
            
            if not articles:
                # 尝试备用选择器（主要新闻）
                articles = soup.select('.c-mainSectionArticle')
            
            self._get_logger().info(f"Found {len(articles)} article elements")
            
            seen_urls = set()
            for article in articles:
                if max_count > 0 and len(news_list) >= max_count:
                    break
                
                # 获取标题和链接
                title_tag = article.select_one('.c-article__title') or article.select_one('.c-mainSectionArticle__title')
                link_tag = article.select_one('a[href]')
                date_tag = article.select_one('.c-article__date') or article.select_one('.c-mainSectionArticle__date')
                
                if not link_tag:
                    continue
                
                href = link_tag.get('href', '')
                title = title_tag.get_text(strip=True) if title_tag else ''
                date_str = date_tag.get_text(strip=True) if date_tag else ''
                
                # 跳过空标题或太短的标题
                if not title or len(title) < 5:
                    continue
                
                # 处理相对路径
                if href.startswith('/'):
                    url = f"https://www3.nhk.or.jp{href}"
                elif href.startswith('http'):
                    url = href
                else:
                    continue
                
                # 跳过非新闻页面
                if any(skip in url.lower() for skip in ['/video', '/audio', '/radio']):
                    continue
                
                # 去重
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # 解析发布日期
                publish_time = self._parse_date(date_str) or datetime.now()
                
                # 抓取正文内容
                content = fetch_article_content(url, self._get_logger())
                
                news_item = NewsItem(
                    title=title,
                    url=url,
                    publish_time=publish_time,
                    content=content,
                    source="nhk"
                )
                
                if self.validate_news_item(news_item):
                    news_list.append(news_item)
                    self._get_logger().info(f"Found news: {title[:50]}...")
            
            self._get_logger().info(f"Successfully fetched {len(news_list)} news from nhk.or.jp/nhkworld")
        
        except Exception as e:
            self._get_logger().error(f"Error parsing nhk.or.jp/nhkworld: {e}")
        
        return news_list