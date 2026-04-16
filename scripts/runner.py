#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import sys
import re
import logging
import os
import feedparser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def clean_content(text, source):
    """
    专门清洗正文污染
    """
    if not text: return ""
    
    # 针对中新网 (chinanews) 的特殊清洗
    if "chinanews" in source.lower() or "中新网" in source:
        # 1. 拦截 "(完)" 之后的所有推荐新闻标题
        # 通常中新网正文结束会有一个 (完) 或 【编辑:xxx】
        stop_keywords = [r"\(完\)", r"【编辑:", r"\[编辑:"]
        for kw in stop_keywords:
            parts = re.split(kw, text)
            if len(parts) > 1:
                text = parts[0] # 只取关键词之前的内容
        
        # 2. 如果发现文本末尾出现大量排在一起的新闻标题（通常缺少句末标点）
        # 我们可以通过正则截断
        text = re.split(r'\n\s*?\n', text)[0] # 尝试通过双换行截断，正文和推荐位通常有大间隙

    # 通用清洗：去除多余空格和连续换行
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

    def fetch_rss_task(self, task, max_count):
        results = []
        try:
            from utils import fetch_article_content # 确保能导入
            feed = feedparser.parse(task['url'])
            for entry in feed.entries[:max_count]:
                raw_content = fetch_article_content(entry.link, logger)
                # 使用清洗函数
                content = clean_content(raw_content or entry.get('summary', ""), task['name'])
                
                results.append({
                    "title": entry.title,
                    "url": entry.link,
                    "content": content,
                    "source": task['name'],
                    "publish_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        except Exception as e:
            logger.error(f"RSS {task['name']} error: {e}")
        return results

    def fetch_crawler_class(self, name, cls, max_count):
        try:
            crawler = cls()
            items = crawler.fetch_news_list(max_count)
            return [
                {
                    "title": it.title, 
                    "url": it.url, 
                    # 同样进行清洗
                    "content": clean_content(it.content, name), 
                    "source": name,
                    "publish_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                } for it in items
            ]
        except Exception as e:
            logger.error(f"Crawler {name} error: {e}")
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