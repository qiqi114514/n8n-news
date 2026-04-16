#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import sys
import re
import logging
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any

import feedparser
from bs4 import BeautifulSoup

# 导入原有爬虫
from crawlers.xinhua import XinhuaCrawler
from crawlers.reuters import ReutersCrawler
from crawlers.people import PeopleCrawler
from crawlers.cctv import CCTVcrawler
from crawlers.chinanews import ChinanewsCrawler
from crawlers.ce import CeCrawler
from crawlers.bbc import BBCcrawler
from crawlers.apnews import APNewsCrawler
from crawlers.guardian import GuardianCrawler
# ... 其他爬虫保持一致

# 配置日志输出到 stderr
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("UnifiedRunner")


class RSSContentExtractor:
    """
    通用的 RSS 文章正文提取器
    支持多种提取策略和自动回退机制，适配不同网站结构
    """
    
    # 常见干扰元素的 CSS 选择器
    BLOCKED_ELEMENTS = [
        'script', 'style', 'noscript', 'nav', 'footer', 'header', 
        'aside', 'iframe', 'form', 'advertisement', '.ad', '.ads', 
        '.advert', '#ad', '#ads', '.sidebar', '.related', '.recommended',
        '.share', '.social', '.comment', '.pagination'
    ]
    
    # 正文结束的常见标记
    END_MARKERS = [
        r'\(完\)', r'【编辑:', r'\[编辑:', r'责任编辑', r'（完）',
        r'THE END', r'▼', r'___', r'\* \*'
    ]
    
    # 无用文本模式
    USELESS_PATTERNS = [
        r'^copyright', r'^©', r'^all rights', r'^privacy policy',
        r'^terms of use', r'^分享到', r'^扫描二维码', r'^点击打开'
    ]
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def extract(self, url: str, html: str, source_name: str = "") -> str:
        """
        提取文章正文，使用多级策略
        
        Args:
            url: 文章 URL
            html: 页面 HTML 内容
            source_name: 来源名称，用于特殊处理
            
        Returns:
            提取的正文内容
        """
        if not html:
            return ""
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 步骤 1: 移除干扰元素
            self._remove_blocked_elements(soup)
            
            # 步骤 2: 尝试多种提取策略
            content = self._try_extraction_strategies(soup, url, source_name)
            
            # 步骤 3: 清洗和后处理
            content = self._clean_content(content, source_name)
            
            if content:
                self.logger.info(f"Extracted {len(content)} chars from {url}")
            else:
                self.logger.warning(f"No content extracted from {url}")
            
            return content
            
        except Exception as e:
            self.logger.error(f"Extraction failed for {url}: {e}", exc_info=True)
            return ""
    
    def _remove_blocked_elements(self, soup: BeautifulSoup):
        """移除干扰元素"""
        for selector in self.BLOCKED_ELEMENTS:
            for element in soup.select(selector):
                element.decompose()
    
    def _try_extraction_strategies(self, soup: BeautifulSoup, url: str, source_name: str) -> str:
        """尝试多种提取策略，按优先级返回第一个成功的结果"""
        
        strategies = [
            ("semantic_tags", self._extract_by_semantic_tags),
            ("css_patterns", self._extract_by_css_patterns),
            ("density_analysis", self._extract_by_density),
            ("paragraph_count", self._extract_by_paragraph_count),
            ("fallback", self._extract_fallback)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                self.logger.debug(f"Trying strategy: {strategy_name} for {url}")
                content = strategy_func(soup, url, source_name)
                if content and len(content.strip()) > 50:
                    self.logger.info(f"Success with strategy: {strategy_name}")
                    return content
            except Exception as e:
                self.logger.debug(f"Strategy {strategy_name} failed: {e}")
                continue
        
        return ""
    
    def _extract_by_semantic_tags(self, soup: BeautifulSoup, url: str, source_name: str) -> str:
        """策略 1: 语义化标签提取"""
        for tag_name in ['article', 'main', 'section']:
            tag = soup.find(tag_name)
            if tag:
                return self._extract_text_from_element(tag)
        return ""
    
    def _extract_by_css_patterns(self, soup: BeautifulSoup, url: str, source_name: str) -> str:
        """策略 2: CSS 类名/ID 模式匹配"""
        patterns = [
            r'articl', r'content', r'post', r'entry', r'story',
            r'body', r'main', r'wrap', r'detail', r'news', r'artical'
        ]
        
        for pattern in patterns:
            # 查找 class
            tag = soup.find(class_=re.compile(pattern, re.I))
            if tag:
                content = self._extract_text_from_element(tag)
                if len(content) > 100:
                    return content
            
            # 查找 id
            tag = soup.find(id=re.compile(pattern, re.I))
            if tag:
                content = self._extract_text_from_element(tag)
                if len(content) > 100:
                    return content
        
        return ""
    
    def _extract_by_density(self, soup: BeautifulSoup, url: str, source_name: str) -> str:
        """策略 3: 文本密度分析"""
        def calculate_density(tag):
            if not hasattr(tag, 'get_text'):
                return 0.0
            html_len = len(str(tag))
            if html_len == 0:
                return 0.0
            text_len = len(tag.get_text(strip=True))
            return text_len / html_len
        
        # 查找所有 div，计算密度
        all_divs = soup.find_all(['div', 'section', 'article'])
        if not all_divs:
            return ""
        
        # 按密度排序
        scored_divs = [(calculate_density(d), len(d.get_text(strip=True)), d) for d in all_divs]
        scored_divs = [(d, score, text_len) for score, text_len, d in scored_divs 
                       if score > 0.2 and text_len > 100]
        
        if scored_divs:
            # 取密度最高且文本量足够的
            best = max(scored_divs, key=lambda x: (x[1], x[2]))
            return self._extract_text_from_element(best[0])
        
        return ""
    
    def _extract_by_paragraph_count(self, soup: BeautifulSoup, url: str, source_name: str) -> str:
        """策略 4: 段落数量统计"""
        all_divs = soup.find_all('div')
        if not all_divs:
            return ""
        
        def count_paragraphs(div):
            return len(div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
        
        best_div = max(all_divs, key=count_paragraphs)
        if count_paragraphs(best_div) >= 3:
            return self._extract_text_from_element(best_div)
        
        return ""
    
    def _extract_fallback(self, soup: BeautifulSoup, url: str, source_name: str) -> str:
        """策略 5: 回退方案 - 提取所有段落"""
        paragraphs = soup.find_all('p')
        texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        return '\n\n'.join(texts)
    
    def _extract_text_from_element(self, element) -> str:
        """从元素中提取并清理文本"""
        if not element:
            return ""
        
        # 提取所有段落
        paragraphs = element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if not paragraphs:
            # 如果没有段落，直接获取文本
            text = element.get_text(separator='\n', strip=True)
            return self._normalize_text(text)
        
        texts = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 10:
                texts.append(text)
        
        return '\n\n'.join(texts)
    
    def _normalize_text(self, text: str) -> str:
        """标准化文本格式"""
        # 替换多个空白字符为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        text = text.strip()
        return text
    
    def _clean_content(self, content: str, source_name: str) -> str:
        """清洗正文内容"""
        if not content:
            return ""
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否为无用文本
            is_useless = False
            for pattern in self.USELESS_PATTERNS:
                if re.match(pattern, line, re.I):
                    is_useless = True
                    break
            
            if is_useless:
                continue
            
            cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # 特殊来源处理
        content = self._handle_source_specific(content, source_name)
        
        # 截断过长内容
        if len(content) > 10000:
            content = content[:10000] + '...'
        
        return content
    
    def _handle_source_specific(self, content: str, source_name: str) -> str:
        """针对特定来源的特殊处理"""
        source_lower = source_name.lower()
        
        # 中新网特殊处理
        if 'chinanews' in source_lower or '中新网' in source_name:
            for marker in self.END_MARKERS:
                match = re.search(marker, content)
                if match:
                    content = content[:match.start()]
                    break
        
        # 其他来源的特殊规则可以在这里添加
        
        return content


def clean_content(text, source):
    """
    兼容旧版本的清洗函数（保留向后兼容）
    """
    if not text:
        return ""
    
    # 针对中新网 (chinanews) 的特殊清洗
    if "chinanews" in source.lower() or "中新网" in source:
        # 1. 拦截 "(完)" 之后的所有推荐新闻标题
        stop_keywords = [r"\(完\)", r"【编辑:", r"\[编辑:"]
        for kw in stop_keywords:
            parts = re.split(kw, text)
            if len(parts) > 1:
                text = parts[0]
        
        # 2. 通过双换行截断
        text = re.split(r'\n\s*?\n', text)[0]

    # 通用清洗
    text = re.sub(r'\n+', '\n', text).strip()
    return text


class UnifiedRunner:
    def __init__(self):
        self.rss_tasks = [
            {"name": "澳门新闻局", "url": "https://govinfohub.gcs.gov.mo/api/rss/n/zh-hans"},
            {"name": "cctv", "url": "https://rsshub.rssforever.com/cctv/world"},
            {"name": "xinhua", "url": "https://rsshub.rssforever.com/news/whxw"},
            {"name": "chinanews", "url": "http://rss.spriple.org/chinanews"}
        ]
        self.crawler_classes = {
           'xinhua': XinhuaCrawler, 'people': PeopleCrawler, 'cctv': CCTVcrawler,
            'chinanews': ChinanewsCrawler, 'reuters': ReutersCrawler, 'ce': CeCrawler,
            'bbc': BBCcrawler, 'apnews': APNewsCrawler, 'guardian': GuardianCrawler
        }
        self.extractor = RSSContentExtractor(logger)

    def fetch_rss_task(self, task, max_count):
        results = []
        try:
            from utils import fetch_html
            feed = feedparser.parse(task['url'])
            
            for entry in feed.entries[:max_count]:
                # 获取 HTML 内容
                html = fetch_html(entry.link, logger)
                
                # 使用新的提取器
                raw_content = self.extractor.extract(entry.link, html or "", task['name'])
                
                # 如果提取失败，回退到 RSS summary
                if not raw_content and entry.get('summary'):
                    raw_content = entry.get('summary')
                
                # 二次清洗（兼容性）
                content = clean_content(raw_content, task['name'])
                
                results.append({
                    "title": entry.title,
                    "url": entry.link,
                    "content": content,
                    "source": task['name'],
                    "publish_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        except Exception as e:
            logger.error(f"RSS {task['name']} error: {e}", exc_info=True)
        return results

    def fetch_crawler_class(self, name, cls, max_count):
        try:
            crawler = cls()
            items = crawler.fetch_news_list(max_count)
            return [
                {
                    "title": it.title, 
                    "url": it.url, 
                    "content": clean_content(it.content, name), 
                    "source": name,
                    "publish_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                } for it in items
            ]
        except Exception as e:
            logger.error(f"Crawler {name} error: {e}", exc_info=True)
            return []

    def start(self, max_count=5):
        all_news = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for r_task in self.rss_tasks:
                futures.append(executor.submit(self.fetch_rss_task, r_task, max_count))
            for name, cls in self.crawler_classes.items():
                futures.append(executor.submit(self.fetch_crawler_class, name, cls, max_count))
            
            for future in as_completed(futures):
                res = future.result()
                if res: all_news.extend(res)
        
        # 最终输出 JSON
        print(json.dumps(all_news, ensure_ascii=False))

if __name__ == "__main__":
    count = 5
    if len(sys.argv) > 1:
        try: count = int(sys.argv[1])
        except: pass
    runner = UnifiedRunner()
    runner.start(max_count=count)