#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import sqlite3
import os
import hashlib
from datetime import datetime

# 路径适配
BASE_DIR = '/app' if os.path.exists('/app') else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'news.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 创建包含聚类和评分字段的表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_raw (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            url TEXT UNIQUE,
            source TEXT,
            published_at TEXT,
            tags TEXT DEFAULT '[]',
            cluster_id TEXT,          
            importance_score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',      
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    
    # 自动升级旧表结构（如果已存在旧表）
    try:
        cursor.execute('ALTER TABLE news_raw ADD COLUMN cluster_id TEXT')
    except: pass
    try:
        cursor.execute('ALTER TABLE news_raw ADD COLUMN importance_score INTEGER DEFAULT 0')
    except: pass
    
    conn.commit()
    conn.close()

def main():
    try:
        # 读取 n8n 传来的 JSON
        input_data = sys.stdin.read()
        if not input_data: return
        
        # 解析可能包含单个项目或项目的数组
        parsed_input = json.loads(input_data)
        items = parsed_input if isinstance(parsed_input, list) else [parsed_input]
        
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 准备批量插入数据
        insert_data = []
        response_items = []

        for item in items:
            # 使用 URL 的 MD5 确保 ID 唯一
            url = item.get("url", "")
            item_id = hashlib.md5(url.encode()).hexdigest()
            
            # 整理标签 (兼容单字符串或列表)
            raw_tags = item.get("tag") or item.get("tags") or ["焦点"]
            tags_list = raw_tags if isinstance(raw_tags, list) else [raw_tags]
            tags_json = json.dumps(tags_list, ensure_ascii=False)

            # 添加到批量插入列表
            insert_data.append((
                item_id,
                item.get("title", ""),
                item.get("content", ""),
                url,
                item.get("source", ""),
                item.get("published_at", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                tags_json,
                item.get("cluster_id"),
                item.get("score") or item.get("importance_score") or 0,
                "pending"
            ))
            
            response_items.append({"status": "success", "id": item_id})

        # 执行批量插入
        cursor.executemany("""
            INSERT INTO news_raw (
                id, title, content, url, source, published_at, 
                tags, cluster_id, importance_score, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
                cluster_id = excluded.cluster_id,
                importance_score = excluded.importance_score,
                tags = excluded.tags,
                title = excluded.title,
                content = excluded.content,
                published_at = excluded.published_at,
                source = excluded.source
        """, insert_data)

        conn.commit()
        conn.close()
        print(json.dumps({"status": "success", "items": response_items}))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    main()