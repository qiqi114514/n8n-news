# -*- coding: utf-8 -*-
"""中国经济网爬虫"""
import re
import requests
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html


class CeCrawler(BaseCrawler):
    """中国经济网新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="ce")
        # 锁定国际频道
        self.base_url = "http://intl.ce.cn/qqss/index.shtml"
        # 中国经济网特有的内容容器选择器
        self.content_selectors = ['#articleText', '#article', '.content', 'div.article']
    
    def fetch_news_list(self, max_count: int = 0) -> List[NewsItem]:
        """抓取中国经济网新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        # 查找包含日期模式的新闻链接（如 /202604/t20260417_xxx.shtml）
        all_links = soup.find_all('a', href=True)
        
        seen_urls = set()
        for a in all_links:
            if max_count > 0 and len(news_list) >= max_count:
                break
            
            url = a.get('href', '')
            title = a.get_text(strip=True)
            
            # 补全相对路径
            if url.startswith('./'):
                url = "http://intl.ce.cn/qqss" + url[1:]
            elif url.startswith('/'):
                url = "http://intl.ce.cn" + url
            
            # 过滤：需要包含日期模式且标题长度足够
            if ('t202' not in url and '/202' not in url) or len(title) < 5 or url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 抓取详情
            content = self._fetch_article_content(url)
            
            news_list.append(NewsItem(
                title=title,
                url=url,
                source="ce",
                content=content or title,
                publish_time=datetime.now()
            ))
        
        return news_list
    
    def _fetch_article_content(self, url: str) -> str:
        """专门针对中国经济网的文章内容提取"""
        logger = self._get_logger()
        
        try:
            # 中国经济网使用 GBK 编码，需要特殊处理
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 尝试多种编码方式
            html = None
            # 首先检查 HTTP 头中的编码信息
            encoding = response.encoding
            if encoding and encoding.lower() in ['gbk', 'gb2312', 'cp936']:
                try:
                    html = response.content.decode(encoding, errors='strict')
                except:
                    pass
            
            # 如果 HTTP 头没有正确编码，尝试 GBK
            if not html:
                try:
                    html = response.content.decode('gbk', errors='strict')
                except:
                    try:
                        html = response.content.decode('gb2312', errors='strict')
                    except:
                        # 最后尝试 utf-8
                        html = response.content.decode('utf-8', errors='ignore')
            
            # 使用 lxml 解析器，它对中文支持更好
            soup = BeautifulSoup(html, 'lxml')
            
            # 移除干扰元素（注意：不要移除 form，因为中国经济网的文章内容在 form#formarticle 内）
            blocked_elements = [
                'script', 'style', 'noscript', 'nav', 'footer', 'header', 'aside',
                'iframe', '.ad', '.ads', '.advert', '#ad', '#ads',
                '.sidebar', '.related', '.recommended', '.share', '.social', '.comment',
                '.pagination', '.copyright', '.p-copyright', '.shouquan', '.function',
                '.ebm', '.video-box', '.player', '.download', '.scan-code', '.qrcode',
                '.author-info', '.publish-time', '.tags', '.categories', '.meta',
                '.breadcrumb', '.toolbar', '.navigation'
            ]
            for element in soup(blocked_elements):
                element.decompose()
            
            # 优先使用中国经济网特有的内容选择器（在移除干扰元素之前查找）
            content_div = None
            for selector in self.content_selectors:
                if selector.startswith('#'):
                    content_div = soup.find(id=selector[1:])
                elif selector.startswith('.'):
                    content_div = soup.find(class_=selector[1:])
                else:
                    content_div = soup.select_one(selector)
                
                if content_div and len(content_div.get_text(strip=True)) > 50:
                    break
            
            # 如果特定选择器没找到，尝试通用方法
            if not content_div:
                from utils import _find_main_content
                content_div = _find_main_content(soup)
            
            if not content_div:
                logger.warning(f"Cannot find content area in {url}")
                return ""
            
            # 提取段落文本
            paragraphs = content_div.find_all(['p'])
            texts = []
            seen_texts = set()
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if (text and len(text) > 20 and len(text) < 2000 and 
                    text not in seen_texts):
                    # 过滤版权等信息，但保留正常新闻内容
                    if not re.search(r'(版权|版权所有|免责声明|联系我们|编辑.*：|责编.*：|发布者 | 来源.*：|转载 | 引用 | 扫描.*二维码 | 关注.*公众号)', text, re.I):
                        texts.append(text)
                        seen_texts.add(text)
            
            # 如果没有找到段落，尝试提取所有文本
            if not texts:
                text = content_div.get_text(strip=True)
                # 清理多余空白
                text = re.sub(r'\s+', ' ', text)
                if len(text) > 50:
                    texts.append(text)
            
            result = '\n\n'.join(texts)
            
            if result:
                logger.info(f"Successfully extracted content from {url}, length: {len(result)} chars")
            else:
                logger.warning(f"No meaningful content extracted from {url}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract article content from {url}: {e}", exc_info=True)
            return ""
