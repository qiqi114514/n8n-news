# -*- coding: utf-8 -*-
"""人民网爬虫"""

from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, parse_datetime, fetch_article_content


class PeopleCrawler(BaseCrawler):
    """人民网新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="people")
        self.base_url = "http://en.people.cn/"
        self.sections = [
            "http://en.people.cn/90882/index.html",  # Society
            "http://en.people.cn/90777/index.html",  # World
            "http://en.people.cn/business/index.html",  # Business
        ]
    
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取人民网新闻列表
        
        Args:
            max_count: 最大抓取条数
            
        Returns:
            NewsItem 列表
        """
        news_list = []
        seen_urls = set()
        
        for section_url in self.sections:
            if len(news_list) >= max_count:
                break
                
            html = fetch_html(section_url, self.logger)
            if not html:
                continue
            
            try:
                soup = BeautifulSoup(html, 'lxml')
                
                # 查找所有链接
                links = soup.find_all('a', href=True)
                
                for link in links:
                    if len(news_list) >= max_count:
                        break
                    
                    title = link.get_text(strip=True)
                    url = link.get('href', '')
                    
                    # 跳过无效链接
                    if not title or not url or len(title) < 10:
                        continue
                    
                    # 只保留包含 /n3/ 或年份的新闻链接
                    if '/n3/' not in url and '/n/' not in url:
                        continue
                    
                    # 处理相对路径
                    if url.startswith('/'):
                        url = f"http://en.people.cn{url}"
                    elif not url.startswith('http'):
                        continue
                    
                    # 去重
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # 提取发布时间
                    publish_time = self._extract_publish_time(url)
                    
                    # 抓取正文内容
                    content = fetch_article_content(url, self.logger)
                    
                    news_item = NewsItem(
                        title=title,
                        url=url,
                        publish_time=publish_time,
                        content=content,
                        source="people"
                    )
                    
                    if self.validate_news_item(news_item):
                        news_list.append(news_item)
                        self.logger.info(f"Found news: {title[:50]}...")
            
            except Exception as e:
                self.logger.error(f"Error parsing section {section_url}: {e}")
        
        self.logger.info(f"Successfully fetched {len(news_list)} news from people.com.cn")
        return news_list
    
    def _extract_publish_time(self, url: str) -> Optional[datetime]:
        """从 URL 中提取发布时间
        
        人民网 URL 格式示例：
        http://en.people.cn/n3/2026/0409/c98649-20444969.html
        """
        try:
            import re
            # 匹配 /YYYY/MMDD/ 格式
            pattern = r'/(\d{4})/(\d{2})(\d{2})/'
            match = re.search(pattern, url)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day))
        except Exception:
            pass
        return None
