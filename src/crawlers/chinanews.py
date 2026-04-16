# -*- coding: utf-8 -*-
"""中国新闻网爬虫"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
import re
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, get_logger


class ChinanewsCrawler(BaseCrawler):
    """中国新闻网新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="chinanews")
        self.base_url = "https://www.chinanews.com.cn/"
    
    def _extract_chinanews_content(self, url: str, html: str) -> str:
        """专门针对中新网的正文提取"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 移除干扰元素
            for selector in ['script', 'style', 'noscript', '.ad', '.ads', '.share', 
                           '.related', '.recommend', '.copyright', 'footer', 'header']:
                for elem in soup.select(selector):
                    elem.decompose()
            
            # 策略 1: 查找专门的 content 区域
            content_div = soup.find(class_=re.compile(r'content|artical|article|main', re.I))
            if not content_div:
                content_div = soup.find(id=re.compile(r'content|artical|article', re.I))
            
            # 策略 2: 查找 article 标签
            if not content_div:
                content_div = soup.find('article')
            
            # 策略 3: 查找包含最多段落的 div
            if not content_div:
                all_divs = soup.find_all('div')
                if all_divs:
                    content_div = max(
                        all_divs,
                        key=lambda d: len(d.find_all('p'))
                    )
            
            if not content_div:
                content_div = soup.find('body') or soup
            
            # 提取段落文本
            paragraphs = content_div.find_all(['p'])
            texts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                # 过滤短文本和版权信息
                if (len(text) > 20 and 
                    not re.search(r'版权 | 所有 | 转载 | 编辑 | 责编 | 分享', text, re.I)):
                    texts.append(text)
            
            # 如果段落太少，尝试提取所有文本块
            if len(texts) < 3:
                for tag in content_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']):
                    text = tag.get_text(strip=True)
                    if (len(text) > 30 and len(text) < 500 and
                        not re.search(r'版权 | 所有 | 转载 | 编辑 | 责编 | 分享 | 扫码', text, re.I)):
                        texts.append(text)
            
            content = '\n\n'.join(texts)
            
            # 截断到结束标记
            end_markers = [r'\(完\)', r'【编辑:', r'\[编辑:', r'责任编辑']
            for marker in end_markers:
                match = re.search(marker, content)
                if match:
                    content = content[:match.start()].strip()
                    break
            
            return content
            
        except Exception as e:
            logger = self._get_logger()
            logger.error(f"Chinanews content extraction failed: {e}")
            return ""
    
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取中国新闻网新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        if not html:
            return news_list
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            seen_urls = set()
            
            for a in soup.find_all('a', href=True):
                if len(news_list) >= max_count:
                    break
                
                url = a['href']
                title = a.get_text(strip=True)
                
                # 过滤无效链接
                if '.shtml' not in url or len(title) < 10:
                    continue
                
                # 处理协议相对 URL
                if url.startswith('//'):
                    url = 'https:' + url
                if url.startswith('/'):
                    url = 'https://www.chinanews.com.cn' + url
                
                # 验证 URL 格式
                if url.count('/') < 5 or url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # 抓取正文内容
                detail_html = fetch_html(url, self._get_logger())
                if detail_html:
                    content = self._extract_chinanews_content(url, detail_html)
                else:
                    content = ""
                
                # 确保有内容
                if not content or len(content) < 30:
                    content = title
                
                news_list.append(NewsItem(
                    title=title,
                    url=url,
                    publish_time=datetime.now(),
                    content=content,
                    source="chinanews"
                ))
        
        except Exception as e:
            self._get_logger().error(f"Chinanews Error: {e}")
        
        return news_list
