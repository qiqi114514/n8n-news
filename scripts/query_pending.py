#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import sqlite3
from collections import defaultdict
import os

BASE_DIR = '/app' if os.path.exists('/app') else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'news.db')

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 明确指定字段顺序，避免解包错误
        cursor.execute("SELECT id, title, content, source, tags, url FROM news_raw WHERE status='pending' LIMIT 50")
        rows = cursor.fetchall()
        conn.close()

        grouped = defaultdict(list)
        for rid, title, content, source, tags_str, url in rows:
            try:
                # 解析标签 JSON 字符串
                tags = json.loads(tags_str) if tags_str else ["焦点"]
            except:
                tags = ["焦点"]
            
            for t in tags:
                grouped[t].append({
                    "id": rid,
                    "title": title,
                    "content": content,
                    "source": source,
                    "url": url
                })

        # 格式化为 n8n 友好的数组
        result = [{"tag": tag, "news_list": articles} for tag, articles in grouped.items()]
        
        # 只输出 JSON 结果
        if not result:
            print(json.dumps([]))
        else:
            print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()