import sys
import json
import sqlite3
import os

BASE_DIR = '/app' if os.path.exists('/app') else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'news.db')

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps([]))
            return
            
        items = json.loads(input_data)
        if not isinstance(items, list):
            items = [items]

        # 设置 timeout 防止数据库忙碌
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        
        # 确保表存在
        cursor.execute("CREATE TABLE IF NOT EXISTS news_raw (url TEXT UNIQUE)")

        new_items = []
        # 使用 Set 提高内存中去重速度
        for item in items:
            url = item.get('url')
            if not url: continue
            
            cursor.execute("SELECT 1 FROM news_raw WHERE url = ? LIMIT 1", (url,))
            if not cursor.fetchone():
                new_items.append(item)
                
        conn.close()
        # 必须打印标准 JSON 给 api_server
        sys.stdout.write(json.dumps(new_items, ensure_ascii=False))
        sys.stdout.flush()

    except Exception as e:
        sys.stderr.write(str(e))
        print(json.dumps([]))

if __name__ == "__main__":
    main()