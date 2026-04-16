#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import sqlite3
import os

BASE_DIR = '/app' if os.path.exists('/app') else os.path.dirname(os.path.abspath(__file__))
# 数据库文件现在位于 data/ 目录
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = str(PROJECT_ROOT / 'data' / 'news.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id TEXT NOT NULL,
            tag_group TEXT,
            summary TEXT,
            sentiment TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(news_id) REFERENCES news_raw(id)
        )
    ''')
    conn.commit()
    conn.close()

def main():
    try:
        # n8n 传来的 payload 应该包含 tag, news_list, 和 llm_response
        input_data = sys.stdin.read()
        if not input_data: return
        payload = json.loads(input_data)
        
        tag = payload.get("tag", "未分类")
        news_list = payload.get("news_list", [])
        # 这里的 llm_response 需要根据你 n8n 的 AI 节点输出结构进行调整
        llm_res = payload.get("llm_response", {})
        
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        success_count = 0
        for news in news_list:
            news_id = news.get("id")
            
            # 1. 插入分析结果
            cursor.execute("""
                INSERT INTO news_analysis (news_id, tag_group, summary, sentiment)
                VALUES (?, ?, ?, ?)
            """, (
                news_id,
                tag,
                llm_res.get("summary", ""),
                llm_res.get("sentiment", "中立")
            ))
            
            # 2. 关键：更新状态，防止新闻被重复分析
            cursor.execute("UPDATE news_raw SET status='analyzed' WHERE id=?", (news_id,))
            success_count += 1

        conn.commit()
        conn.close()
        print(json.dumps({"status": "success", "processed": success_count, "tag": tag}))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()