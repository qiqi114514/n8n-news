#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import sqlite3
import os
from pathlib import Path

# 路径逻辑
BASE_DIR = '/app' if os.path.exists('/app') else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'news.db')

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data: return
        payload = json.loads(input_data)
        
        # 接收标题列表
        titles = payload.get("titles", [])
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if titles:
            # 批量根据 title 更新状态
            placeholders = ', '.join(['?'] * len(titles))
            cursor.execute(f"UPDATE news_raw SET status = 'analyzed' WHERE title IN ({placeholders})", titles)

        conn.commit()
        conn.close()
        print(json.dumps({"status": "success", "updated": len(titles)}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()