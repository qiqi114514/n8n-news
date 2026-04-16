import streamlit as st
import sqlite3
import pandas as pd
import streamlit.components.v1 as components
import re

# 1. 页面基本配置
st.set_page_config(
    page_title="AI 首席情报官 - 控制塔",
    page_icon="📡",
    layout="wide"
)

# 2. 数据库连接函数（加入异常捕获）
def get_db_connection():
    try:
        conn = sqlite3.connect('news.db', check_same_thread=False)
        return conn
    except Exception as e:
        st.error(f"❌ 无法连接数据库: {e}")
        return None

# --- 数据清洗逻辑：修复换行符渲染问题 ---
def clean_html_content(raw_html):
    if not raw_html:
        return ""
    
    import json
    processed = raw_html

    # 1. 尝试处理 JSON 转义（这是最常见的乱码来源）
    # 如果字符串看起来像 "{\"summary\":...}"，尝试将其解析为真正的 HTML 内容
    if processed.startswith('{') or processed.startswith('"'):
        try:
            # 尝试通过 JSON 解码处理转义符
            data = json.loads(processed)
            if isinstance(data, dict):
                # 优先寻找可能存入 HTML 的字段
                processed = data.get('raw_response', data.get('full_markdown', str(data)))
            else:
                processed = data
        except:
            pass

    # 2. 处理 Unicode 乱码的核心逻辑
    if '\\u' in processed or '\\n' in processed:
        try:
            # 使用 raw-unicode-escape 处理已被错误编码的中文
            processed = processed.encode('latin-1').decode('unicode_escape')
        except:
            try:
                processed = processed.encode('utf-8').decode('unicode_escape')
            except:
                pass

    # 3. 彻底剔除 Markdown 标签和反斜杠转义
    processed = re.sub(r'^```html\s*', '', processed, flags=re.IGNORECASE)
    processed = re.sub(r'\s*```$', '', processed)
    processed = processed.replace('\\"', '"').replace('\\n', '\n')
    
    return processed

# 3. 侧边栏：实时监控
st.sidebar.title("📊 系统实时监控")
conn = get_db_connection()

if conn:
    try:
        # 检查表是否存在
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
        if 'news_raw' in tables.values:
            status_df = pd.read_sql("SELECT status as '状态', COUNT(*) as '数量' FROM news_raw GROUP BY status", conn)
            st.sidebar.table(status_df)
            
            source_df = pd.read_sql("SELECT source as '来源', COUNT(*) as '条数' FROM news_raw GROUP BY source", conn)
            st.sidebar.bar_chart(source_df.set_index('来源'))
        else:
            st.sidebar.warning("等待数据入库...")
    except Exception as e:
        st.sidebar.error(f"监控数据读取失败: {e}")

# 4. 主界面
st.title("📡 AI 智能情报分析门户")
st.markdown("---")

tab1, tab2 = st.tabs(["📅 深度日报预览", "📦 原始数据流水"])

with tab1:
    st.header("最新行业深度分析")
    if conn:
        try:
            # 读取分析表
            analysis_data = pd.read_sql(
                "SELECT created_at, raw_response FROM news_analysis ORDER BY created_at DESC LIMIT 15", 
                conn
            )
            
            if not analysis_data.empty:
                selected_date = st.selectbox("📅 选择报告期数", analysis_data['created_at'])
                raw_content = analysis_data[analysis_data['created_at'] == selected_date]['raw_response'].values[0]
                
                # 执行清洗逻辑
                final_html = clean_html_content(raw_content)
                
                # 渲染
                st.markdown("---")
                # 增加高度以适应长日报
                components.html(final_html, height=1000, scrolling=True)
            else:
                st.info("💡 暂无分析记录，请检查 n8n 的『早晚报分析』工作流是否正常存库。")
        except Exception as e:
            st.error(f"❌ 读取分析表失败: {e}")

with tab2:
    st.header("实时入库新闻 (Top 50)")
    if conn:
        try:
            raw_news_df = pd.read_sql(
                "SELECT title as '标题', source as '来源', status as '状态', created_at as '入库时间' FROM news_raw ORDER BY created_at DESC LIMIT 50",
                conn
            )
            st.dataframe(raw_news_df, use_container_width=True)
        except Exception as e:
            st.error(f"❌ 读取原始表失败: {e}")

# 逻辑优化：确保在页面结束前关闭连接
if conn:
    conn.close()

if st.button("🔄 刷新页面数据"):
    st.rerun()