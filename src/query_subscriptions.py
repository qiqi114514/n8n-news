import sqlite3
import os
import json
from datetime import datetime, timedelta, timezone

def get_user_news_payload():
    # 数据库路径逻辑
    BASE_DIR = '/app' if os.path.exists('/app') else os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'news.db')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # --- 核心时区锁定逻辑 ---
    # 强制创建中国时区 (UTC+8)
    tz_utc8 = timezone(timedelta(hours=8))
    # 获取当前的北京时间
    now = datetime.now(tz_utc8)
    
    current_date = now.strftime('%Y-%m-%d')
    hour = now.hour
    
    # 判定当前应该是发“早间”还是“晚间”
    # 注意：这里判断的是北京时间的小时数
    if 8 <= hour <= 10:
        target_time_label = f"{current_date} 早间"
    elif 20 <= hour <= 22:
        target_time_label = f"{current_date} 晚间"
    else:
        # 如果不在推送时间段内，返回空列表，避免误发
        conn.close()
        return []

    # 1. 获取所有订阅者
    cursor.execute("SELECT user_email, GROUP_CONCAT(interested_tag) FROM subscriptions GROUP BY user_email")
    subscribers = cursor.fetchall()
    
    final_output = []
    
    for email, tags_str in subscribers:
        tags_list = tags_str.split(',')
        
        # 2. 根据该用户订阅的标签，且匹配当前的 time 标签进行查询
        placeholders = ', '.join(['?'] * len(tags_list))
        query = f"""
            SELECT tag, html_content 
            FROM reports 
            WHERE tag IN ({placeholders}) 
            AND time = ?
        """
        # 参数绑定
        cursor.execute(query, tags_list + [target_time_label]) 
        report_items = cursor.fetchall()
        
        if not report_items:
            continue
            
        # 3. 拼接邮件内容
        report_type = "早报" if "早间" in target_time_label else "晚报"
        # 显示北京时间的生成时间
        combined_html = f"<h2>您的今日定向{report_type}</h2><p>报告生成时间（北京时间）：{now.strftime('%Y-%m-%d %H:%M')}</p>"
        
        for tag, content in report_items:
            combined_html += f"<div style='border-left: 4px solid #007bff; padding: 10px; margin-bottom: 20px; background: #f8f9fa;'>"
            combined_html += f"<h3 style='color: #007bff;'>【{tag}板块 · {report_type}】</h3>"
            combined_html += content
            combined_html += "</div><hr>"
            
        final_output.append({
            "email": email,
            "subject": f"【{report_type}】今日定制：{ ' & '.join(tags_list) } 板块分析",
            "full_html": combined_html
        })
        
    conn.close()
    return final_output

if __name__ == "__main__":
    # n8n 捕获此输出时将获得标准中国时区判定的数据
    print(json.dumps(get_user_news_payload()))