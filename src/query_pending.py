#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
import os

from pathlib import Path

def get_db_path():
    """获取数据库路径，优先检测容器环境，其次使用本地相对路径"""
    if os.path.exists('/app'):
        # 在容器环境中，数据库文件直接在/app目录下
        return '/app/news.db'
    
    # 对于主机环境，使用脚本所在目录的相对路径
    script_dir = Path(__file__).parent
    return str(script_dir / 'news.db')

def ensure_full_table_structure(db_path):
    """Ensure the news_raw table has all required columns"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table with full structure if it doesn't exist
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
    
    # Check for and add missing columns with error handling
    columns_and_types = [
        ('id', 'TEXT'),
        ('title', 'TEXT'),
        ('content', 'TEXT'),
        ('source', 'TEXT'),
        ('published_at', 'TEXT'),
        ('tags', "TEXT DEFAULT '[]'"),
        ('cluster_id', 'TEXT'),
        ('importance_score', 'INTEGER DEFAULT 0'),
        ('status', "TEXT DEFAULT 'pending'"),
        ('created_at', "TEXT DEFAULT (datetime('now'))")
    ]
    
    for col_name, col_type in columns_and_types:
        try:
            # Try to select from the column to see if it exists
            cursor.execute(f'SELECT {col_name} FROM news_raw LIMIT 1')
        except sqlite3.OperationalError:
            # Column doesn't exist, so add it
            try:
                if 'DEFAULT' in col_type:
                    base_type = col_type.split('DEFAULT')[0].strip()
                    cursor.execute(f'ALTER TABLE news_raw ADD COLUMN {col_name} {base_type}')
                    # Set default value for existing rows if table isn't empty
                    default_part = col_type.split('DEFAULT')[1].strip()
                    cursor.execute(f'UPDATE news_raw SET {col_name} = {default_part} WHERE {col_name} IS NULL')
                else:
                    cursor.execute(f'ALTER TABLE news_raw ADD COLUMN {col_name} {col_type}')
            except sqlite3.OperationalError:
                # If adding the column fails, continue with next column
                pass
    
    conn.commit()
    conn.close()

def main():
    try:
        # 获取数据库路径
        db_path = get_db_path()
        
        # 确认数据库文件存在
        if not os.path.exists(db_path):
            try:
                # 尝试列出数据库目录下的文件，帮助调试
                db_dir = os.path.dirname(db_path)
                files = os.listdir(db_dir) if os.path.exists(db_dir) else "Directory does not exist"
                error_msg = {
                    "error": f"Database file not found: {db_path}",
                    "available_at": files,
                    "db_dir_exists": os.path.exists(db_dir),
                    "expected_path": db_path
                }
            except Exception as e:
                error_msg = {"error": f"Database file not found and error getting directory contents: {str(e)}"}
            
            print(json.dumps(error_msg))
            return
        
        print(f"Connecting to database at: {db_path}")
        
        # Ensure the database has the correct structure
        ensure_full_table_structure(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 根据当前时间决定查询的时间范围
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # 如果是早上8:20左右执行，查询前一天晚上9点到今天早上8点的数据
        if (current_hour == 8 and current_minute <= 20) or (current_hour == 7 and current_minute >= 50):
            # 计算时间范围
            # 昨天晚上9点: 昨天21:00:00
            # 今天早上8点: 今天08:00:00
            query = """
            SELECT title, source, tags, importance_score, content, url 
            FROM news_raw 
            WHERE status = 'pending' 
              AND created_at BETWEEN datetime('now', '-1 day', '21:00:00') 
                               AND datetime('now', '08:00:00')
            """
        # 如果是晚上8:20左右执行，查询今天早上9点到当前晚上8点20分的数据
        elif (current_hour == 20 and current_minute >= 20) or (current_hour == 21 and current_minute <= 5):  # 晚上8:20到9:05之间
            # 计算时间范围
            # 今天早上9点: 今天09:00:00  
            # 今天晚上8:20: 今天20:20:00
            query = """
            SELECT title, source, tags, importance_score, content, url 
            FROM news_raw 
            WHERE status = 'pending' 
              AND created_at BETWEEN datetime('now', '09:00:00') 
                               AND datetime('now', '20:20:00')
            """
        # 如果是其他时间执行，我们可以默认使用第一种情况或者提供一个默认查询
        else:
            # 默认查询最近24小时内的pending数据
            query = """
            SELECT title, source, tags, importance_score, content, url 
            FROM news_raw 
            WHERE status = 'pending' 
              AND created_at >= datetime('now', '-1 day')
            """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        # 将结果转换为所需格式
        result = []
        for title, source, tags_str, importance_score, content, url in rows:
            try:
                # 解析标签 JSON 字符串，处理空值和'null'字符串
                if tags_str and tags_str != 'null':
                    try:
                        tags = json.loads(tags_str)
                    except Exception as e:
                        print(f"Error parsing tags: {e}, raw tags: {tags_str}")
                        tags = ["焦点"]
                else:
                    tags = ["焦点"]
            except Exception as e:
                print(f"Error parsing tags: {e}")
                tags = ["焦点"]
                
            # 为每个标签创建一个条目
            for tag in tags:
                result.append({
                    "title": title,
                    "source": source,
                    "tag": tag,
                    "importance_score": importance_score,
                    "content": content,
                    "url": url
                })
        
        # 输出 JSON 结果
        if not result:
            print(json.dumps([]))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
    except sqlite3.Error as e:
        print(json.dumps({"error": f"Database error: {str(e)}"}))
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}))

if __name__ == "__main__":
    main()