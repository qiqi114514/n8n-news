# -*- coding: utf-8 -*-
"""AP News 爬虫"""

from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content


class APNewsCrawler(BaseCrawler):
    """AP News 爬虫"""
    
    def __init__(self):
        super().__init__(name="apnews")
        self.base_url = "https://apnews.com"
    
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取 AP News 新闻列表
        
        Args:
            max_count: 最大抓取条数
            
        Returns:
            NewsItem 列表
        """
        news_list = []
        
        # AP News 首页
        url = "https://apnews.com"
        html = fetch_html(url, self.logger)
        
        if not html:
            self.logger.error("Failed to fetch apnews.com")
            return news_list
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 查找新闻链接
            articles = []
            
            # AP News 常用的选择器
            selectors = [
                '.CardHeadline a',
                '.CardTitle a',
                'article a',
                'a[href*="/article/"]',
                'a[href*="/wire/"]',
                '.PagePromoModule a',
                '.feed-story a',
                '.story-card a'
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
                    url = f"https://apnews.com{url}"
                elif not url.startswith('http'):
                    continue
                
                # 去重
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # 提取发布时间（AP News 通常在页面中）
                publish_time = None
                
                # 抓取正文内容
                content = fetch_article_content(url, self.logger)
                
                news_item = NewsItem(
                    title=title,
                    url=url,
                    publish_time=publish_time,
                    content=content,
                    source="apnews"
                )
                
                if self.validate_news_item(news_item):
                    news_list.append(news_item)
                    self.logger.info(f"Found news: {title[:50]}...")
            
            self.logger.info(f"Successfully fetched {len(news_list)} news from apnews.com")
            
        except Exception as e:
            self.logger.error(f"Error parsing apnews.com: {e}")
        
        return news_list
