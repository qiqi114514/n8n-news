# -*- coding: utf-8 -*-
"""Reuters 爬虫"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content


class ReutersCrawler(BaseCrawler):
    """Reuters 新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="reuters")
        self.base_url = "https://www.reuters.com/world/"
    
    def fetch_news_list(self, max_count: int = 10) -> list[NewsItem]:
        """抓取 Reuters 新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        seen_urls = set()
        
        for a in soup.find_all('a', href=True):
            if len(news_list) >= max_count:
                break
            
            url = a['href']
            title = a.get_text(strip=True)
            
            # 过滤无效链接
            if '/article/' not in url and not re.search(r'/\d{4}-\d{2}-\d{2}/', url):
                continue
            if len(title) < 20:
                continue
            
            # 处理完整 URL
            full_url = url if url.startswith('http') else f"https://www.reuters.com{url}"
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            # 抓取正文内容
            content = fetch_article_content(full_url, self._get_logger())
            if content:
                # 清理尾部信息
                content = re.split(r'Reporting by|Editing by|Our Standards:', content)[0]
                if len(content) > 800:
                    content = content[:800] + "..."
            
            news_list.append(NewsItem(
                title=title,
                url=full_url,
                source="reuters",
                content=(content or title).strip(),
                publish_time=datetime.now()
            ))
        
        return news_list