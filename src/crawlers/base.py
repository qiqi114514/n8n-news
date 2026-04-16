# -*- coding: utf-8 -*-
"""爬虫抽象基类"""
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils import get_logger


class NewsItem:
    """新闻条目数据类"""
    
    def __init__(
        self,
        title: str,
        url: str,
        publish_time: Optional[datetime] = None,
        source: str = "",
        summary: str = "",
        content: str = ""
    ):
        self.title = title
        self.url = url
        self.publish_time = publish_time
        self.source = source
        self.summary = summary
        self.content = content
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "url": self.url,
            "publish_time": self.publish_time.strftime("%Y-%m-%d %H:%M:%S") if self.publish_time else None,
            "source": self.source,
            "summary": self.summary,
            "content": self.content
        }


class BaseCrawler(ABC):
    def __init__(self, name: str = "base"):
        self.name = name
        self.logger = get_logger(f"crawler.{name}")
        
        # ✅ 1. 定义一组常用的 User-Agent 列表
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/121.0.0.0"
        ]
        
        # ✅ 2. 随机选择一个 UA 并完善 Headers
        self.headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
    
    @abstractmethod
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取新闻列表（抽象方法，子类必须实现）
        
        Args:
            max_count: 最大抓取条数
            
        Returns:
            NewsItem 列表
        """
        pass  # ✅ 抽象方法只保留 pass
    
    def validate_news_item(self, item: NewsItem) -> bool:
        """验证新闻条目是否有效"""
        if not item.title or not item.url:
            self.logger.warning(f"Invalid news item: missing title or url")
            return False
        return True
    
    def filter_news(
        self, 
        news_list: List[NewsItem], 
        max_count: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[NewsItem]:
        """过滤新闻列表"""
        filtered = []
        
        for item in news_list:
            if not self.validate_news_item(item):
                continue
            if start_date and item.publish_time and item.publish_time < start_date:
                continue
            if end_date and item.publish_time and item.publish_time > end_date:
                continue
            filtered.append(item)
            if len(filtered) >= max_count:
                break
        
        return filtered