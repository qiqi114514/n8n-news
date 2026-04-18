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
from crawlers.ce import CeCrawler
from crawlers.bbc import BBCcrawler
from crawlers.apnews import APNewsCrawler
from crawlers.guardian import GuardianCrawler
from crawlers.nhk import NHKCrawler
from crawlers.dw import DWCrawler


# 配置日志输出到 stderr
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("UnifiedRunner")


class RSSContentExtractor:
    """
    智能 RSS 正文提取器
    策略：通过评分系统找到最可能的正文容器，避免重复和噪音
    """
    
    # 干扰元素选择器 (直接移除)
    NEGATIVE_PATTERNS = [
        'script', 'style', 'iframe', 'noscript', 'meta', 'link', 'svg',
        '.advertisement', '.ads', '.sidebar', '.footer', '.header',
        '.nav', '.menu', '.share', '.social', '.comment', '.related',
        '[class*="ad-"]', '[id*="ad-"]', '[class*="share"]', '[id*="share"]',
        '[class*="copyright"]', '[id*="copyright"]', '[class*="disclaimer"]'
    ]

    # 正文特征关键词 (加分项)
    POSITIVE_PATTERNS = [
        'content', 'article', 'post', 'body', 'main', 'story', 'text',
        'entry', 'detail', 'news', 'information', 'description', 'left_zw'
    ]

    # 负面特征关键词 (减分项)
    NEGATIVE_KEYWORDS = [
        'copyright', '广告', '推荐', '相关阅读', '猜你喜欢', '分享到',
        '二维码', '扫一扫', '责编', '编辑', '来源', '版权声明', '免责声明',
        '转载', '作者', '出处', '本网', '本网站', '本站', '原创', '未经授权',
        '保留所有权利', 'all rights reserved', '©'
    ]

    def extract(self, url: str, html: str, source_name: str = "") -> str:
        """
        主入口：提取正文
        """
        if not html:
            return ""

        soup = BeautifulSoup(html, 'lxml')
        
        # 1. 预处理：移除干扰元素
        self._remove_noise(soup)
        
        # 2. 特殊源处理
        self._handle_source_specific(soup, url, source_name)

        # 3. 核心策略：评分查找最佳正文容器
        best_container = self._find_best_container(soup)
        
        if best_container:
            text = self._clean_container_text(best_container)
            if len(text) > 50:  # 只有长度足够才返回
                return text
        
        # 4. 降级策略：如果找不到容器，尝试直接提取所有段落并去重
        return self._fallback_extract(soup)
    
    def _remove_noise(self, soup: BeautifulSoup):
        """移除已知的干扰元素"""
        for pattern in self.NEGATIVE_PATTERNS:
            try:
                elements = soup.select(pattern)
                for el in elements:
                    el.decompose()
            except Exception:
                continue

    def _handle_source_specific(self, soup: BeautifulSoup, url: str, source_name: str):
        """针对特定网站的特殊处理"""
        pass

    def _find_best_container(self, soup: BeautifulSoup):
        """
        评分算法：遍历所有包含文本的标签，计算得分，返回最高分的标签
        评分规则：
        + 文本长度 (主要权重)
        + 包含 <p> 标签数量
        + 命中正面关键词
        - 命中负面关键词
        - 文本密度过低 (说明链接/代码太多)
        """
        candidates = []
        
        # 只遍历可能包含正文的标签
        for tag in soup.find_all(['div', 'section', 'article', 'td']):
            text = tag.get_text(separator=' ', strip=True)
            if len(text) < 50:  # 太短的忽略
                continue
            
            score = 0
            
            # 1. 文本长度分 (每 10 字得 1 分，上限 50 分)
            score += min(len(text) / 10, 50)
            
            # 2. 段落分 (每个 <p> 得 5 分)
            p_count = len(tag.find_all('p'))
            score += p_count * 5
            
            # 3. 关键词加分/减分
            class_str = " ".join(tag.get('class', [])) + " " + tag.get('id', '')
            for word in self.POSITIVE_PATTERNS:
                if word in class_str.lower() or word in tag.name.lower():
                    score += 10
            
            for word in self.NEGATIVE_KEYWORDS:
                if word in text.lower() or word in class_str.lower():
                    score -= 20
            
            # 4. 密度惩罚 (如果链接文本占比超过 30%，扣分)
            links_text = " ".join([a.get_text(strip=True) for a in tag.find_all('a')])
            if len(text) > 0:
                link_ratio = len(links_text) / len(text)
                if link_ratio > 0.3:
                    score -= 15
            
            candidates.append((score, tag))

        if not candidates:
            return None
        
        # 按分数排序，取最高分
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_tag = candidates[0]
        
        # 只有分数达到一定阈值才认为是正文 (防止抓取到侧边栏列表)
        if best_score > 20 or (len(best_tag.find_all('p')) >= 1 and best_score > 10):
            logger.debug(f"Best container found with score {best_score}: {best_tag.name} class={best_tag.get('class')}")
            return best_tag
        
        return None

    def _clean_container_text(self, container) -> str:
        """
        清理容器内的文本：
        1. 移除子级干扰
        2. 提取文本
        3. 去重行
        """
        # 再次清理容器内部的残留干扰
        for el in container.find_all(['script', 'style', 'img', 'br']):
            el.decompose()

        texts = []
        seen_lines = set()
        
        # 优先提取 p 标签，如果没有 p 则提取所有文本
        paragraphs = container.find_all('p')
        if not paragraphs:
            paragraphs = [container]
            
        for p in paragraphs:
            line = p.get_text(separator=' ', strip=True)
            if not line:
                continue
            
            # 过滤短行和负面行
            if len(line) < 5:
                continue
            if any(k in line.lower() for k in ['版权声明', '责任编辑', '扫码下载', '分享到', '版权所有', 'copyright', 'all rights reserved', '原创', '不得转载', '作者', '编辑', '责编', '来源']):
                continue
            
            # 简单的去重：如果这一行完全出现过，跳过
            if line in seen_lines:
                continue
            
            # 避免包含大量标题的重复 (如果一行和上一行相似度极高)
            if texts and len(line) > 10 and line in texts[-1]:
                continue
                
            seen_lines.add(line)
            texts.append(line)
        
        return "\n\n".join(texts)

    def _fallback_extract(self, soup: BeautifulSoup) -> str:
        """
        降级方案：当找不到明显容器时，收集所有符合条件的段落
        """
        paragraphs = soup.find_all('p')
        valid_texts = []
        seen = set()
        
        for p in paragraphs:
            txt = p.get_text(strip=True)
            if len(txt) < 20:
                continue
            if any(k in txt.lower() for k in ['版权', '版权所有', '广告', 'copyright', 'all rights reserved', '原创', '不得转载', '作者', '编辑', '责编', '来源']):
                continue
            if txt in seen:
                continue
            
            seen.add(txt)
            valid_texts.append(txt)
        
        # 如果收集到的文本太少，尝试提取 body 全文
        if len(valid_texts) < 2:
            body = soup.find('body')
            if body:
                # 过滤掉body中的版权和元数据
                for tag in body.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                full_text = body.get_text(separator='\n', strip=True)
                
                # 按行分割并过滤版权信息
                lines = full_text.split('\n')
                filtered_lines = []
                for line in lines:
                    if len(line) > 20 and not any(k in line.lower() for k in ['版权', '版权所有', '广告', 'copyright', 'all rights reserved', '原创', '不得转载', '作者', '编辑', '责编', '来源']):
                        filtered_lines.append(line)
                
                return "\n\n".join(filtered_lines)[:2000]
                
        return "\n\n".join(valid_texts)


def clean_content(text, source):
    """
    兼容旧版本的清洗函数（保留向后兼容）
    """
    if not text:
        return ""

    # 通用清洗
    text = re.sub(r'\n+', '\n', text).strip()
    
    # 新增：去除常见的版权和元数据信息
    # 移除开头和结尾的版权信息
    text = re.sub(r'^.*?版权.*?\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^.*?免责声明.*?\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^.*?编辑.*?\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^.*?责编.*?\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^.*?作者.*?\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^.*?出处.*?\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^.*?来源.*?\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # 移除末尾的版权信息
    text = re.sub(r'\n.*?版权.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\n.*?免责声明.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\n.*?编辑.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\n.*?责编.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\n.*?作者.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\n.*?出处.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\n.*?来源.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # 移除重复的标题
    lines = text.split('\n')
    unique_lines = []
    seen_lines = set()
    
    for line in lines:
        stripped_line = line.strip()
        if stripped_line and stripped_line not in seen_lines and len(stripped_line) > 10:
            unique_lines.append(stripped_line)
            seen_lines.add(stripped_line)
    
    text = '\n'.join(unique_lines)
    
    return text


class UnifiedRunner:
    def __init__(self):
        self.rss_tasks = [
            {"name": "澳门新闻局", "url": "https://govinfohub.gcs.gov.mo/api/rss/n/zh-hans"},
            {"name": "xinhua", "url": "https://rsshub.rssforever.com/news/whxw"},
            {"name": "afp", "url": "https://rsshub.rssforever.com/yahoo/news/provider/hk/afp.com.hk"},
	        {"name": "afp", "url": "https://rsshub.rssforever.com/twitter/user/afp"},
            {"name": "dw", "url": "https://rss.dw.com/atom/rss-en-all"}
        ]
        self.crawler_classes = {
           'xinhua': XinhuaCrawler, 'people': PeopleCrawler, 
             'reuters': ReutersCrawler, 'ce': CeCrawler,
            'bbc': BBCcrawler, 'apnews': APNewsCrawler, 'guardian': GuardianCrawler,
            'nhk': NHKCrawler, 'dw': DWCrawler
        }
        self.extractor = RSSContentExtractor()

    def fetch_rss_task(self, task, max_count):
        results = []
        try:
            from utils import fetch_html
            feed = feedparser.parse(task['url'])
            
            for entry in feed.entries[:max_count]:
                # 获取 HTML 内容
                html = fetch_html(entry.link, logger)
                
                # 使用新的提取器 (移除 logger 参数)
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