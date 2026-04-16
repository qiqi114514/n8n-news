# -*- coding: utf-8 -*-
"""央视网爬虫"""
import re
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html


class CCTVcrawler(BaseCrawler):
    """央视网新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="cctv")
        self.base_url = "https://news.cctv.com/"
    
    def _extract_cctv_content(self, url: str, html: str) -> str:
        """专门针对央视网的正文提取"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 移除所有干扰元素（扩展选择器）
            blocked_selectors = [
                'script', 'style', 'noscript', 'nav', 'footer', 'header', 'aside',
                '.ad', '.ads', '.advert', '#ad', '#ads', '.sidebar', '.related',
                '.recommend', '.share', '.social', '.comment', '.pagination',
                '.copyright', '.p-copyright', '.shouquan', '.function', '.ebm',
                '.video-box', '.player', '.download', '.scan-code', '.qrcode'
            ]
            for selector in blocked_selectors:
                for elem in soup.select(selector):
                    elem.decompose()
            
            # 策略 1: 查找央视网特有的内容区域
            content_area = (
                soup.select_one('#content_area') or
                soup.select_one('#text_area') or
                soup.select_one('.cnt_bd') or
                soup.select_one('.content_area') or
                soup.select_one('.text_area') or
                soup.find('article')
            )
            
            # 策略 2: 通过 class/id 模式匹配
            if not content_area:
                content_area = soup.find(class_=re.compile(r'content|article|main|detail|text', re.I))
            if not content_area:
                content_area = soup.find(id=re.compile(r'content|article|main|detail|text', re.I))
            
            # 策略 3: 查找包含最多段落的 div
            if not content_area:
                all_divs = soup.find_all('div')
                if all_divs:
                    content_area = max(
                        all_divs,
                        key=lambda d: len(d.find_all(['p', 'h1', 'h2', 'h3']))
                    )
            
            if not content_area:
                content_area = soup.find('body') or soup
            
            # 提取段落文本
            paragraphs = content_area.find_all(['p'])
            texts = []
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                # 过滤条件：长度、版权信息、无关内容
                if (len(text) > 20 and 
                    len(text) < 2000 and
                    not re.search(r'版权 | 所有 | 转载 | 编辑 | 责编 | 分享 | 扫码 | 下载|APP', text, re.I) and
                    not text.startswith(('http', 'www.'))):
                    texts.append(text)
            
            # 如果段落太少，尝试从标题和其他块提取
            if len(texts) < 3:
                # 提取标题
                title_tags = content_area.find_all(['h1', 'h2', 'h3', 'h4'])
                for tag in title_tags:
                    text = tag.get_text(strip=True)
                    if 10 < len(text) < 200 and text not in texts:
                        texts.insert(0, text)  # 标题放前面
                
                # 提取其他文本块
                for div in content_area.find_all(['div', 'span']):
                    text = div.get_text(strip=True)
                    if (30 < len(text) < 1000 and 
                        not re.search(r'版权 | 所有 | 转载 | 编辑 | 分享', text, re.I)):
                        # 检查是否已存在相似文本
                        if not any(abs(len(t) - len(text)) < 20 for t in texts):
                            texts.append(text)
            
            content = '\n\n'.join(texts)
            
            # 清理重复和多余空白
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            cleaned_lines = []
            seen = set()
            for line in lines:
                if line not in seen and len(line) > 5:
                    cleaned_lines.append(line)
                    seen.add(line)
            
            content = '\n\n'.join(cleaned_lines)
            
            return content
            
        except Exception as e:
            logger = self._get_logger()
            logger.error(f"CCTV content extraction failed: {e}")
            return ""
    
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取央视网新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        if not html:
            return news_list
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            all_links = soup.find_all('a', href=True)
            seen_urls = set()
            
            for a in all_links:
                if len(news_list) >= max_count:
                    break
                
                url = a['href']
                title = a.get_text(strip=True)
                
                # 过滤无效链接
                if not re.search(r'/202\d/', url) or '.shtml' not in url:
                    continue
                if len(title) < 10 or url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # 处理协议相对 URL
                if url.startswith('//'):
                    url = 'https:' + url
                
                # 抓取正文内容
                detail_html = fetch_html(url, self._get_logger())
                if detail_html:
                    content = self._extract_cctv_content(url, detail_html)
                else:
                    content = ""
                
                # 确保有足够的内容
                if not content or len(content) < 50:
                    # 尝试获取 meta description 作为备选
                    if detail_html:
                        detail_soup = BeautifulSoup(detail_html, 'lxml')
                        meta_desc = detail_soup.find('meta', attrs={'name': 'description'})
                        if meta_desc and meta_desc.get('content'):
                            content = meta_desc['content']
                    
                    # 如果还是没内容，使用提示语
                    if not content or len(content) < 20:
                        content = f"（同步央视新闻：{title}）请点击链接查看详情。"
                
                news_list.append(NewsItem(
                    title=title,
                    url=url,
                    source="cctv",
                    content=content.strip(),
                    publish_time=datetime.now()
                ))
        
        except Exception as e:
            self._get_logger().error(f"CCTV Error: {e}")
        
        return news_list
