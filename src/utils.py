# -*- coding: utf-8 -*-
"""工具函数模块：请求/日志/时间处理"""

import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import requests
from bs4 import BeautifulSoup, Tag

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


def _extract_text_with_density(element: Tag, min_density: float = 0.3) -> List[str]:
    """基于文本密度提取高质量文本内容
    
    Args:
        element: BeautifulSoup 元素
        min_density: 最小文本密度阈值（文本长度/HTML 长度）
        
    Returns:
        提取的文本段落列表
    """
    texts = []
    
    def calculate_density(tag: Tag) -> float:
        """计算文本密度"""
        if not isinstance(tag, Tag):
            return 0.0
        
        html_len = len(str(tag))
        if html_len == 0:
            return 0.0
        
        text_len = len(tag.get_text(strip=True))
        return text_len / html_len
    
    def extract_recursive(tag: Tag):
        """递归提取高密度文本块"""
        if not isinstance(tag, Tag):
            return
        
        # 跳过脚本和样式
        if tag.name in ['script', 'style', 'noscript']:
            return
        
        density = calculate_density(tag)
        
        # 如果是叶子节点且密度足够高
        if density >= min_density and len(tag.get_text(strip=True)) > 30:
            text = tag.get_text(strip=True)
            # 清理多余空白
            text = re.sub(r'\s+', ' ', text)
            if len(text) > 30:
                texts.append(text)
        else:
            # 继续递归子节点
            for child in tag.children:
                if isinstance(child, Tag):
                    extract_recursive(child)
    
    extract_recursive(element)
    return texts


def _find_main_content(soup: BeautifulSoup) -> Tag:
    """智能查找主要内容区域
    
    Args:
        soup: BeautifulSoup 对象
        
    Returns:
        包含主要内容的标签
    """
    # 优先级 1: 语义化标签
    semantic_tags = ['article', 'main', 'section']
    for tag_name in semantic_tags:
        tag = soup.find(tag_name)
        if tag:
            return tag
    
    # 优先级 2: 通过 class/id 识别
    content_patterns = [
        r'articl', r'content', r'post', r'entry', r'story', 
        r'body', r'main', r'wrap', r'detail'
    ]
    
    # 查找匹配的 class
    for pattern in content_patterns:
        tag = soup.find(class_=re.compile(pattern, re.I))
        if tag:
            return tag
    
    # 查找匹配的 id
    for pattern in content_patterns:
        tag = soup.find(id=re.compile(pattern, re.I))
        if tag:
            return tag
    
    # 优先级 3: 查找包含最多段落的容器
    all_divs = soup.find_all('div')
    if all_divs:
        best_div = max(
            all_divs, 
            key=lambda d: len(d.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
        )
        if len(best_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])) > 2:
            return best_div
    
    # 默认返回整个 body 或 html
    body = soup.find('body')
    return body if body else soup


def _clean_extracted_texts(texts: List[str], max_length: int = 10000) -> str:
    """清理和合并提取的文本
    
    Args:
        texts: 文本段落列表
        max_length: 最大总长度
        
    Returns:
        清理后的完整文本
    """
    cleaned = []
    seen = set()
    
    for text in texts:
        # 清理空白和特殊字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 过滤条件
        if (not text or 
            len(text) < 20 or 
            text in seen or
            text.lower().startswith(('copyright', '©', 'all rights', 'privacy policy')) or
            len(text) > 2000):  # 避免单个过长的块（可能是导航或侧边栏）
            continue
        
        seen.add(text)
        cleaned.append(text)
        
        # 检查总长度
        current_total = sum(len(t) for t in cleaned)
        if current_total >= max_length:
            break
    
    result = '\n\n'.join(cleaned)
    if len(result) > max_length:
        result = result[:max_length] + '...'
    
    return result


def fetch_article_content(url: str, logger: Optional[logging.Logger] = None) -> str:
    """抓取文章正文内容（优化版）
    
    使用多种策略提取正文：
    1. 语义化标签识别（article, main, section）
    2. CSS 类名/ID 模式匹配
    3. 文本密度分析
    4. 段落数量统计
    
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
        
        # 移除干扰元素
        for element in soup(['script', 'style', 'noscript', 'nav', 'footer', 
                            'header', 'aside', 'iframe', 'form', 'advertisement', 
                            '.ad', '.ads', '.advert', '#ad', '#ads']):
            element.decompose()
        
        # 智能查找主内容区域
        main_container = _find_main_content(soup)
        
        # 提取文本：结合传统段落提取和密度分析
        all_texts = []
        
        # 方法 1: 提取段落
        paragraphs = main_container.find_all(['p'])
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                all_texts.append(text)
        
        # 方法 2: 密度分析提取（补充段落遗漏的内容）
        dense_texts = _extract_text_with_density(main_container, min_density=0.25)
        all_texts.extend(dense_texts)
        
        # 清理和合并
        content = _clean_extracted_texts(all_texts)
        
        if content:
            logger.info(f"Successfully extracted content from {url}, length: {len(content)} chars")
        else:
            logger.warning(f"No meaningful content extracted from {url}")
        
        return content
        
    except Exception as e:
        logger.error(f"Failed to extract article content from {url}: {e}", exc_info=True)
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
