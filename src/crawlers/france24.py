# -*- coding: utf-8 -*-
"""France 24 爬虫"""
from typing import List
from datetime import datetime
import re
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content


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
    
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取 France 24 新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        
        if not html:
            self._get_logger().error("Failed to fetch france24.com")
            return news_list
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            articles = []
            
            # France 24 常用的选择器
            selectors = [
                'article a',
                '.m-article-list__content a',
                '.c-tile__content a',
                'a[href*="/en/"]',
                'a[href*="/fr/"]',
                'a[href*="/es/"]',
                'a[href*="/ar/"]',
                '.m-listing--live a',
                '.m-listing--highlights a'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    articles.extend(elements)
                    if len(articles) >= max_count * 2:
                        break
            
            # 去重并处理
            seen_urls = set()
            for item in articles:
                if len(news_list) >= max_count:
                    break
                
                # 获取标题和链接
                if hasattr(item, 'get') and item.get('href'):
                    title = item.get_text(strip=True)
                    url = item['href']
                else:
                    a_tag = item.find('a') if hasattr(item, 'find') else item
                    if a_tag and hasattr(a_tag, 'get'):
                        title = a_tag.get_text(strip=True)
                        url = a_tag.get('href', '')
                    else:
                        continue
                
                if not title or not url:
                    continue
                
                # 跳过空标题或太短的标题
                if len(title) < 5:
                    continue
                
                # 处理相对路径
                if url.startswith('/'):
                    url = f"https://www.france24.com{url}"
                elif not url.startswith('http'):
                    continue
                
                # 跳过非新闻页面
                if any(skip in url.lower() for skip in ['/live', '/video', '/podcast', '/watch']):
                    continue
                
                # 去重
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # 抓取正文内容
                content = fetch_article_content(url, self._get_logger())
                
                news_item = NewsItem(
                    title=title,
                    url=url,
                    publish_time=datetime.now(),
                    content=content,
                    source="france24"
                )
                
                if self.validate_news_item(news_item):
                    news_list.append(news_item)
                    self._get_logger().info(f"Found news: {title[:50]}...")
            
            self._get_logger().info(f"Successfully fetched {len(news_list)} news from france24.com")
        
        except Exception as e:
            self._get_logger().error(f"Error parsing france24.com: {e}")
        
        return news_list