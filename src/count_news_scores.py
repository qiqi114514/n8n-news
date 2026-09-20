#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统计news.db数据库中news_raw表的新闻分数分布
"""
import sqlite3
from pathlib import Path

def get_db_path():
    """获取数据库路径"""
    base_dir = '/app' if Path('/app').exists() else Path(__file__).parent
    return str(base_dir / 'news.db')

def count_news_by_scores():
    """统计不同分数区间的新闻数量"""
    db_path = get_db_path()
    
    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        # 连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询数据库表结构，确认importance_score字段是否存在
        cursor.execute("PRAGMA table_info(news_raw)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'importance_score' not in columns:
            print("警告: news_raw表中没有importance_score字段")
            # 尝试使用其他可能的字段名
            possible_fields = ['score', 'importance', 'rating']
            found_field = False
            for field in possible_fields:
                if field in columns:
                    print(f"使用字段 '{field}' 替代 importance_score")
                    score_column = field
                    found_field = True
                    break
            if not found_field:
                print("错误: 找不到分数相关的字段")
                conn.close()
                return
        else:
            score_column = 'importance_score'
        
        # 查询0分新闻的数量
        cursor.execute(f"SELECT COUNT(*) FROM news_raw WHERE {score_column} = 0")
        zero_score_count = cursor.fetchone()[0]
        
        # 查询1-6分新闻的数量
        cursor.execute(f"SELECT COUNT(*) FROM news_raw WHERE {score_column} BETWEEN 1 AND 6")
        low_score_count = cursor.fetchone()[0]
        
        # 查询7-10分新闻的数量
        cursor.execute(f"SELECT COUNT(*) FROM news_raw WHERE {score_column} BETWEEN 7 AND 10")
        high_score_count = cursor.fetchone()[0]
        
        # 总数
        cursor.execute(f"SELECT COUNT(*) FROM news_raw")
        total_count = cursor.fetchone()[0]
        
        # 输出结果
        print("=" * 50)
        print("新闻分数分布统计:")
        print("=" * 50)
        print(f"0分新闻数量:     {zero_score_count:,}")
        print(f"1-6分新闻数量:   {low_score_count:,}")
        print(f"7-10分新闻数量:  {high_score_count:,}")
        print("-" * 50)
        print(f"新闻总数:        {total_count:,}")
        print("=" * 50)
        
        # 额外输出各具体分数的详细统计
        print("\n各具体分数统计:")
        print("-" * 30)
        for score in range(11):  # 0-10分
            cursor.execute(f"SELECT COUNT(*) FROM news_raw WHERE {score_column} = ?", (score,))
            count = cursor.fetchone()[0]
            print(f"{score}分: {count:,}")
        
        conn.close()
        
    except Exception as e:
        print(f"查询过程中发生错误: {e}")

if __name__ == "__main__":
    count_news_by_scores()