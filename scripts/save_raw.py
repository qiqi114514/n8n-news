#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import sqlite3
import logging
import os
import hashlib
from datetime import datetime

# 路径配置
BASE_DIR = '/app' if os.path.exists('/app') else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'news.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_raw (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            url TEXT UNIQUE,
            source TEXT,
            published_at TEXT,
            tags TEXT DEFAULT '[]',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    conn.commit()
    conn.close()

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data: return
        item = json.loads(input_data)
        
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 使用 URL 的 MD5 确保 ID 唯一且稳定
        url = item.get("url", "")
        item_id = hashlib.md5(url.encode()).hexdigest()
        
        # 使用 INSERT OR IGNORE 彻底防止 URL 重复导致的报错
        cursor.execute("""
            INSERT INTO news_raw (id, title, content, url, source, published_at, tags, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
                status = CASE WHEN status = 'analyzed' THEN 'analyzed' ELSE 'pending' END
        """, (
            item_id,
            item.get("title", ""),
            item.get("content", ""),
            url,
            item.get("source", ""),
            item.get("published_at", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            json.dumps(item.get("tags", []) if item.get("tags") else ["焦点"], ensure_ascii=False),
            "pending"
        ))

        conn.commit()
        conn.close()
        print(json.dumps({"saved": 1, "id": item_id, "title": item.get("title")}, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()