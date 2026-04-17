#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
定时新闻爬虫调度器
每隔一小时爬取新闻，并追加保存到同一个 JSON 档案文件中
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.crawlers.xinhua import XinhuaCrawler
from src.crawlers.reuters import ReutersCrawler
from src.crawlers.people import PeopleCrawler
from src.crawlers.ce import CeCrawler
from src.crawlers.bbc import BBCcrawler
from src.crawlers.apnews import APNewsCrawler
from src.crawlers.guardian import GuardianCrawler
from src.crawlers.nhk import NHKCrawler
from src.config import MAX_NEWS_COUNT

# 默认数据目录
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_ARCHIVE_FILE = DATA_DIR / "raw" / "news_archive.json"

# 爬虫映射表
CRAWLER_MAP = {
    'xinhua': XinhuaCrawler,
    'reuters': ReutersCrawler,
    'people': PeopleCrawler,
    'ce': CeCrawler,
    'bbc': BBCcrawler,
    'apnews': APNewsCrawler,
    'guardian': GuardianCrawler,
    'nhk': NHKCrawler,
}


def load_archive(archive_path: str) -> List[Dict[str, Any]]:
    """加载现有的档案文件
    
    Args:
        archive_path: 档案文件路径
        
    Returns:
        现有的新闻数据列表
    """
    if not os.path.exists(archive_path):
        return []
    
    try:
        with open(archive_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                print(f"Warning: Archive file format unexpected, starting fresh.", file=sys.stderr)
                return []
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse archive file ({e}), starting fresh.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Failed to load archive file ({e}), starting fresh.", file=sys.stderr)
        return []


def save_archive(archive_path: str, news_data: List[Dict[str, Any]]) -> None:
    """保存新闻数据到档案文件
    
    Args:
        archive_path: 档案文件路径
        news_data: 新闻数据列表
    """
    # 创建临时文件以确保原子写入
    temp_path = archive_path + ".tmp"
    
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        # 原子替换原文件
        os.replace(temp_path, archive_path)
        print(f"Saved archive with {len(news_data)} total news items to {archive_path}", file=sys.stderr)
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e


def crawl_all_sources(max_count: int = MAX_NEWS_COUNT, source_filter: str = 'all') -> List[Dict[str, Any]]:
    """抓取所有新闻源的数据
    
    Args:
        max_count: 每个源最大抓取条数
        source_filter: 指定新闻源，'all' 表示所有源
        
    Returns:
        新闻数据列表（字典格式）
    """
    all_news = []
    
    # 确定要抓取的源
    if source_filter == 'all':
        sources_to_crawl = CRAWLER_MAP.items()
    else:
        if source_filter not in CRAWLER_MAP:
            print(f"Unknown source: {source_filter}", file=sys.stderr)
            return all_news
        sources_to_crawl = [(source_filter, CRAWLER_MAP[source_filter])]
    
    # 初始化所有爬虫
    for source_name, crawler_class in sources_to_crawl:
        try:
            crawler = crawler_class()
            news_list = crawler.fetch_news_list(max_count=max_count)
            for item in news_list:
                news_dict = item.to_dict()
                # 添加爬取时间戳
                news_dict['crawl_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                all_news.append(news_dict)
            print(f"Crawled {len(news_list)} items from {source_name}", file=sys.stderr)
        except Exception as e:
            print(f"Error crawling {source_name}: {e}", file=sys.stderr)
    
    return all_news


def run_once(archive_path: str, max_count: int, source_filter: str) -> int:
    """执行一次爬取任务
    
    Args:
        archive_path: 档案文件路径
        max_count: 每个源最大抓取条数
        source_filter: 指定新闻源
        
    Returns:
        本次爬取的新闻数量
    """
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Starting crawl at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    # 加载现有档案
    existing_news = load_archive(archive_path)
    print(f"Loaded {len(existing_news)} existing items from archive", file=sys.stderr)
    
    # 爬取新新闻
    new_news = crawl_all_sources(max_count=max_count, source_filter=source_filter)
    print(f"Crawled {len(new_news)} new items", file=sys.stderr)
    
    # 追加到现有数据
    all_news = existing_news + new_news
    
    # 保存到档案
    save_archive(archive_path, all_news)
    
    return len(new_news)


def run_scheduler(
    archive_path: str,
    interval_hours: int = 1,
    max_count: int = MAX_NEWS_COUNT,
    source_filter: str = 'all'
) -> None:
    """运行定时调度器
    
    Args:
        archive_path: 档案文件路径
        interval_hours: 爬取间隔（小时）
        max_count: 每个源最大抓取条数
        source_filter: 指定新闻源
    """
    interval_seconds = interval_hours * 3600
    
    print(f"News Crawler Scheduler Started", file=sys.stderr)
    print(f"Archive file: {archive_path}", file=sys.stderr)
    print(f"Interval: {interval_hours} hour(s)", file=sys.stderr)
    print(f"Max count per source: {max_count}", file=sys.stderr)
    print(f"Source filter: {source_filter}", file=sys.stderr)
    print(f"Press Ctrl+C to stop\n", file=sys.stderr)
    
    try:
        while True:
            start_time = datetime.now()
            
            # 执行一次爬取
            new_count = run_once(archive_path, max_count, source_filter)
            
            # 计算下次执行时间
            next_run = start_time.timestamp() + interval_seconds
            next_run_str = datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\nNext crawl scheduled at: {next_run_str}", file=sys.stderr)
            print(f"Waiting {interval_hours} hour(s)...", file=sys.stderr)
            
            # 等待到下次执行时间
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user.", file=sys.stderr)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='News Crawler Scheduler - 定时爬取新闻并保存到档案文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 运行一次爬取并保存
  python scheduler.py --once
  
  # 启动定时调度器（每小时爬取一次）
  python scheduler.py
  
  # 每 2 小时爬取一次
  python scheduler.py --interval 2
  
  # 只爬取特定新闻源
  python scheduler.py --source xinhua
  
  # 指定档案文件路径
  python scheduler.py --output /path/to/archive.json
        """
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='只运行一次爬取，不启动定时调度'
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=1,
        help='爬取间隔时间（小时），默认：1'
    )
    
    parser.add_argument(
        '-n', '--count',
        type=int,
        default=MAX_NEWS_COUNT,
        help=f'每个源最大抓取条数 (默认：{MAX_NEWS_COUNT})'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=DEFAULT_ARCHIVE_FILE,
        help=f'档案文件路径 (默认：{DEFAULT_ARCHIVE_FILE})'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        choices=list(CRAWLER_MAP.keys()) + ['all'],
        default='all',
        help='指定新闻源 (默认：all)'
    )
    
    args = parser.parse_args()
    
    if args.once:
        # 只运行一次
        new_count = run_once(args.output, args.count, args.source)
        print(f"\nCompleted! Crawled {new_count} new items.", file=sys.stderr)
    else:
        # 启动定时调度器
        run_scheduler(
            archive_path=args.output,
            interval_hours=args.interval,
            max_count=args.count,
            source_filter=args.source
        )


if __name__ == '__main__':
    main()
