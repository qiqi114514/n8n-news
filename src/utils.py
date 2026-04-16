# -*- coding: utf-8 -*-
"""工具函数模块：请求/日志/时间处理"""

import logging
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import HEADERS, REQUEST_TIMEOUT, LOG_LEVEL, LOG_FORMAT


def get_logger(name: str) -> logging.Logger:
    """获取配置好的日志记录器"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL))
    return logger


def fetch_html(url: str, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """发送 HTTP GET 请求获取页面内容"""
    if logger is None:
        logger = get_logger(__name__)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        logger.info(f"Successfully fetched: {url}")
        return response.text
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def fetch_article_content(url: str, logger: Optional[logging.Logger] = None) -> str:
    """抓取文章正文内容
    
    Args:
        url: 文章 URL
        logger: 日志记录器
        
    Returns:
        文章正文内容
    """
    if logger is None:
        logger = get_logger(__name__)
    
    try:
        html = fetch_html(url, logger)
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'lxml')
        
        # 移除不需要的元素
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'form']):
            element.decompose()
        
        # 尝试常见的文章内容容器
        content_containers = [
            soup.find('article'),
            soup.find(class_=lambda x: x and any(k in x.lower() for k in ['article-content', 'article-body', 'post-content', 'entry-content', 'story-body', 'content-body'])),
            soup.find(id=lambda x: x and any(k in x.lower() for k in ['article-content', 'article-body', 'post-content', 'entry-content', 'story-body', 'content-body'])),
        ]
        
        # 选择最合适的容器
        main_container = None
        for container in content_containers:
            if container:
                main_container = container
                break
        
        if not main_container:
            main_container = soup
        
        # 提取所有段落文本，避免重复
        paragraphs = main_container.find_all(['p'])
        content_parts = []
        seen_texts = set()
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            # 过滤掉太短或可能是标题/导航的文本
            if text and len(text) > 20 and text not in seen_texts:
                seen_texts.add(text)
                content_parts.append(text)
        
        # 如果没有找到段落，尝试从其他标签提取
        if not content_parts:
            divs = main_container.find_all('div', string=lambda t: t and len(t.strip()) > 50)
            for div in divs:
                text = div.get_text(strip=True)
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    content_parts.append(text)
        
        # 合并内容，限制总长度
        full_content = '\n\n'.join(content_parts)
        max_length = 10000  # 限制最大长度
        if len(full_content) > max_length:
            full_content = full_content[:max_length] + '...'
        
        logger.info(f"Extracted article content from {url}, length: {len(full_content)}")
        return full_content
        
    except Exception as e:
        logger.error(f"Failed to extract article content from {url}: {e}")
        return ""


def parse_datetime(date_str: str) -> Optional[datetime]:
    """解析日期字符串为 datetime 对象
    
    支持多种常见格式：
    - 2024-01-15 10:30:00
    - 2024/01/15 10:30:00
    - 2024-01-15
    - 2024/01/15
    - Jan 15, 2024
    """
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def format_datetime(dt: datetime, output_format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化 datetime 对象为字符串"""
    return dt.strftime(output_format)


def get_current_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
