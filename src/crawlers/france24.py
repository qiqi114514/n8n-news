# -*- coding: utf-8 -*-
"""France 24 爬虫"""
from typing import List
from datetime import datetime
import re
import feedparser
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, get_logger, _clean_extracted_texts


class France24Crawler(BaseCrawler):
    """France 24 新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="france24")
        self.base_url = "https://www.france24.com/en/"
        self.rss_feeds = [
            "https://www.france24.com/en/rss",
            "https://www.france24.com/en/rss/europe",
            "https://www.france24.com/en/rss/world/",
        ]
    
    def fetch_article_content(self, url: str) -> str:
        """专门针对France24的文章内容提取方法"""
        logger = self._get_logger()
        
        try:
            html = fetch_html(url, logger)
            if not html:
                return ""
            
            soup = BeautifulSoup(html, 'lxml')
            
            # 更新的干扰元素列表，特别针对France24
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
                '.article-nav', '.read-next', '.post-navigation',
                '.f24--content-header', '.f24--sticky-share', '.f24--taboola',
                '.f24--disqus', '.f24--newsletter-form', '.f24--tags-container',
                '.article-share', '.article-related', '.article-author',
                '.o-aside-content', '.o-footer', '.o-header', '.a-site-nav', '.m-follow-entity',
                '.m-tag-body', '.m-article-medias', '.m-article-related', '.m-article-share',
                '.a-comments-wrapper', '.m-breaking-alert', '.o-sticky-wrapper',
                '[data-testid="taboola"]', '[data-testid="ads"]', '.tms-ad', '.t-content__aside'
            ]
            for element in soup(blocked_elements):
                element.decompose()
            
            # 法国24的主要内容区域选择器，按优先级排列
            content_selectors = [
                'div.t-content__body',  # 最重要的内容主体
                'div.f24--content-body',
                'article.f24--content-article',
                'div.t-content__main',
                'div.t-content',
                'article'
            ]
            
            content_div = None
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div and content_div.get_text(strip=True):
                    break
            
            # 如果上面的选择器都没找到，使用通用方法
            if not content_div:
                from utils import _find_main_content
                content_div = _find_main_content(soup)
            
            if not content_div:
                logger.warning(f"Cannot find content area in {url}")
                return ""
            
            # 提取段落文本
            paragraphs = content_div.find_all(['p', 'div'], recursive=True)
            texts = []
            seen_texts = set()
            
            for p in paragraphs:
                # 排除包含链接过多的段落（通常是导航或广告）
                links = p.find_all('a')
                text = p.get_text(strip=True)
                
                # 跳过太短或太长的文本
                if len(text) < 20 or len(text) > 2000:
                    continue
                
                # 跳过已见过的文本
                if text in seen_texts:
                    continue
                
                # 过滤版权、编辑、标签等相关信息
                if re.search(r'(Copyright|copyright|©|All rights reserved|All Rights Reserved|Editor|Author|Published on|Tags?|Category|Related|Advertisement|Subscribe|Newsletter|Follow us|Sign up|Download the|Mobile app|Mobile application|Read more|Continue reading)', text, re.I):
                    continue
                
                # 过滤社交媒体和分享相关信息
                if re.search(r'(Share|Tweet|Facebook|Twitter|LinkedIn|WhatsApp|Email|Print|Copy link|comments|Leave a comment|See all comments|Post a comment)', text, re.I):
                    continue
                
                # 检查段落是否包含过多链接，如果是则跳过
                link_ratio = 0
                if len(text) > 0 and links:
                    link_text = ''.join([a.get_text() for a in links])
                    link_ratio = len(link_text) / len(text)
                
                if link_ratio > 0.5:  # 如果一半以上都是链接文字，则跳过
                    continue
                
                # 跳过只有少量文字的标题类元素
                if p.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and len(text) < 10:
                    continue
                
                texts.append(text)
                seen_texts.add(text)
            
            # 使用项目标准的文本清理函数
            result = _clean_extracted_texts(texts)
            
            if result:
                logger.info(f"Successfully extracted content from {url}, length: {len(result)} chars")
            else:
                logger.warning(f"No meaningful content extracted from {url}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract article content from {url}: {e}", exc_info=True)
            return ""

    def fetch_news_list(self, max_count: int = 0) -> List[NewsItem]:
        """抓取 France 24 新闻列表
        
        Args:
            max_count: 最大抓取条数，0 表示不限制
            
        Returns:
            NewsItem 列表
        """
        news_list = []
        logger = self._get_logger()
        
        for rss_url in self.rss_feeds:
            try:
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries:
                    if max_count > 0 and len(news_list) >= max_count:
                        break
                    
                    title = entry.get('title', '').strip()
                    url = entry.get('link', '').strip()
                    
                    if not title or not url:
                        continue
                    
                    # 跳过非英语页面
                    if '/fr/' in url or '/es/' in url or '/ar/' in url:
                        continue
                    
                    # 获取发布时间
                    publish_time = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            publish_time = datetime(*entry.published_parsed[:6])
                        except Exception:
                            publish_time = datetime.now()
                    else:
                        publish_time = datetime.now()
                    
                    # 使用专门的方法抓取正文内容
                    content = self.fetch_article_content(url)
                    
                    news_item = NewsItem(
                        title=title,
                        url=url,
                        publish_time=publish_time,
                        content=content,
                        source="france24"
                    )
                    
                    if self.validate_news_item(news_item):
                        news_list.append(news_item)
                        logger.info(f"Found news: {title[:50]}...")
                
                if max_count > 0 and len(news_list) >= max_count:
                    break
                    
            except Exception as e:
                logger.error(f"Error parsing RSS feed {rss_url}: {e}")
        
        logger.info(f"Successfully fetched {len(news_list)} news from france24.com")
        return news_list