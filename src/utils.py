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
        
        # 更严格的过滤：移除包含版权、编辑、责编等信息的段落
        if re.search(r'(版权|版权所有|免责声明|联系我们|编辑|责编|发布者|来源|转载|引用|原文链接|出处|作者|记者|通讯员|报道|整理|校对|扫描二维码|关注.*公众号|订阅.*|广告|推荐|相关文章|热门文章|评论|留言|反馈)', text, re.I):
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
    """抓取文章正文内容（增强版）
    
    使用多种策略提取正文：
    1. 语义化标签识别（article, main, section）
    2. CSS 类名/ID 模式匹配（扩展模式）
    3. 文本密度分析
    4. 段落数量统计
    5. 标题和子标题提取
    
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
        
        # 移除干扰元素（扩展列表）
        blocked_elements = [
            'script', 'style', 'noscript', 'nav', 'footer', 'header', 'aside',
            'iframe', 'form', 'advertisement', '.ad', '.ads', '.advert', '#ad', '#ads',
            '.sidebar', '.related', '.recommended', '.share', '.social', '.comment',
            '.pagination', '.copyright', '.p-copyright', '.shouquan', '.function',
            '.ebm', '.video-box', '.player', '.download', '.scan-code', '.qrcode',
            '.author-info', '.publish-time', '.tags', '.categories', '.meta',
            '.article-info', '.post-meta', '.article-meta', '.news-meta',
            '.breadcrumb', '.toolbar', '.nav', '.navigation', '.more-stories',
            '.related-articles', '.recommended-articles', '.article-tags',
            '.article-nav', '.read-next', '.post-navigation'
        ]
        for element in soup(blocked_elements):
            element.decompose()
        
        # 智能查找主内容区域
        main_container = _find_main_content(soup)
        
        # 多策略提取文本
        all_texts = []
        seen_texts = set()
        
        # 策略 1: 提取段落（主要来源）
        paragraphs = main_container.find_all(['p'])
        for p in paragraphs:
            text = p.get_text(strip=True)
            if (text and len(text) > 20 and len(text) < 2000 and 
                text not in seen_texts):
                # 更严格的过滤版权等信息
                if not re.search(r'(版权|版权所有|免责声明|联系我们|编辑|责编|发布者|来源|转载|引用|原文链接|出处|作者|记者|通讯员|报道|整理|校对|扫描二维码|关注.*公众号|订阅.*|广告|推荐|相关文章|热门文章|评论|留言|反馈)', text, re.I):
                    all_texts.append(text)
                    seen_texts.add(text)
        
        # 策略 2: 提取标题和子标题
        title_tags = main_container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for tag in title_tags:
            text = tag.get_text(strip=True)
            if (text and 10 < len(text) < 200 and 
                text not in seen_texts and
                not re.search(r'(版权|所有|发布者|来源|编辑|责编|记者|通讯员|整理|校对)', text, re.I)):
                all_texts.insert(0, text)  # 标题放前面
                seen_texts.add(text)
        
        # 策略 3: 密度分析提取（补充遗漏内容）
        dense_texts = _extract_text_with_density(main_container, min_density=0.25)
        for text in dense_texts:
            if text not in seen_texts and len(text) > 30:
                # 过滤版权和不相关内容
                if not re.search(r'(版权|版权所有|免责声明|联系我们|编辑|责编|发布者|来源|转载|引用|原文链接|出处|作者|记者|通讯员|报道|整理|校对|扫描二维码|关注.*公众号|订阅.*|广告|推荐|相关文章|热门文章|评论|留言|反馈)', text, re.I):
                    all_texts.append(text)
                    seen_texts.add(text)
        
        # 策略 4: 如果内容太少，尝试从整个页面提取
        if len(all_texts) < 3:
            # 查找所有包含较多文本的 div
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)
                if (50 < len(text) < 1500 and 
                    text not in seen_texts and
                    not re.search(r'(版权|所有|发布者|编辑|责编|来源|转载|引用|原文链接|出处|作者|记者|通讯员|报道|整理|校对|扫描二维码|关注.*公众号|订阅.*|广告|推荐|相关文章|热门文章|评论|留言|反馈)', text, re.I)):
                    # 检查是否与已有文本重复
                    if not any(len(t) - 50 < len(text) < len(t) + 50 for t in all_texts):
                        all_texts.append(text)
                        seen_texts.add(text)
        
        # 额外策略 5: 检测并过滤重复段落（避免连续相同内容）
        deduplicated_texts = []
        for i, text in enumerate(all_texts):
            is_duplicate = False
            for j, existing_text in enumerate(deduplicated_texts):
                # 检查两个文本是否有高度重叠（去除空格后相似度很高）
                clean_text = re.sub(r'\s+', '', text)
                clean_existing = re.sub(r'\s+', '', existing_text)
                
                # 如果一个文本是另一个的子集且占比较高，则认为是重复
                if len(clean_text) > 0 and len(clean_existing) > 0:
                    if clean_text in clean_existing or clean_existing in clean_text:
                        if abs(len(clean_text) - len(clean_existing)) < max(len(clean_text), len(clean_existing)) * 0.3:
                            is_duplicate = True
                            break
            
            if not is_duplicate:
                deduplicated_texts.append(text)
        
        # 清理和合并
        content = _clean_extracted_texts(deduplicated_texts)
        
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