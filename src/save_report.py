#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# 路径逻辑
BASE_DIR = '/app' if os.path.exists('/app') else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'news.db')

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data: return
        payload = json.loads(input_data)
        
        tag = payload.get("tag", "未分类")
        html_content = payload.get("html_content", "")
        
        # 获取当前时间并判断是早间还是晚间
        now = datetime.now()
        hour = now.hour
        time_label = "早间" if hour < 9 else "晚间"
        # 格式化时间为 YYYY-MM-DD 早间/晚间
        formatted_time = f"{now.strftime('%Y-%m-%d')} {time_label}"

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 确保表存在
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag TEXT NOT NULL,
                html_content TEXT,
                time TEXT NOT NULL
            )
        ''')

        # 插入报告内容
        cursor.execute("INSERT INTO reports (tag, html_content, time) VALUES (?, ?, ?)", (tag, html_content, formatted_time))

        conn.commit()
        conn.close()
        print(json.dumps({"status": "success"}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()