import streamlit as st
import sqlite3
import pandas as pd
import streamlit.components.v1 as components
import re
import hashlib
from pathlib import Path

# 1. 页面基本配置
st.set_page_config(
    page_title="AI 智能情报分析门户",
    page_icon="📡",
    layout="wide"
)

# 2. 数据库连接函数（加入异常捕获）
def get_db_connection():
    try:
        # 数据库文件现在位于 src/ 目录
        db_path = Path(__file__).parent / 'news.db'
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
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
                # 优先寻找可能存入 HTML 的 fields
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

def init_analysis_table():
    """Initialize news_analysis table if it doesn't exist"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_response TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.commit()
        except Exception as e:
            st.error(f"初始化分析表失败：{e}")
        finally:
            conn.close()

def init_users_table():
    """Initialize users table if it doesn't exist"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.commit()
        except Exception as e:
            st.error(f"初始化用户表失败：{e}")
        finally:
            conn.close()

def init_subscriptions_table():
    """Initialize subscriptions table if it doesn't exist"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    interested_tag TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.commit()
        except Exception as e:
            st.error(f"初始化订阅表失败：{e}")
        finally:
            conn.close()

# --- 用户认证辅助函数 ---
def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user."""
    return stored_password == hash_password(provided_password)

def register_user(name, email, password):
    """Register a user by adding them to the users table."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Check if user already exists in either users or admin_users table
            cursor.execute("SELECT 1 FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return False, "邮箱已被注册"
                
            cursor.execute("SELECT 1 FROM admin_users WHERE email = ?", (email,))
            if cursor.fetchone():
                return False, "邮箱已在管理员账户中注册"
            
            # Insert user into users table
            password_hash = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                (name, email, password_hash, 0)
            )
            conn.commit()
            return True, "注册成功！请前往登录页签登录。"
        except Exception as e:
            st.error(f"注册失败: {e}")
            return False, f"注册失败: {e}"
        finally:
            conn.close()
    return False, "数据库连接失败"

def login_user(email, password):
    """Login user and return user info if successful."""
    conn = get_db_connection()
    if conn:
        try:
            # 检查是否是管理员账户
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, email, password_hash FROM admin_users WHERE email = ?
            """, (email,))
            admin_result = cursor.fetchone()
            
            if admin_result:
                # 验证管理员密码
                if verify_password(admin_result[2], password):
                    conn.close()
                    return {
                        "user_name": admin_result[0], 
                        "user_email": admin_result[1], 
                        "is_admin": True
                    }
            
            # 检查普通用户
            cursor.execute("""
                SELECT username, email, password_hash FROM users WHERE email = ?
            """, (email,))
            user_result = cursor.fetchone()
            
            if user_result:
                if verify_password(user_result[2], password):
                    conn.close()
                    return {
                        "user_name": user_result[0], 
                        "user_email": user_result[1], 
                        "is_admin": False
                    }
            else:
                # 兼容旧的订阅表中的用户（降级模式）
                cursor.execute("""
                    SELECT DISTINCT user_name, user_email FROM subscriptions WHERE user_email = ? LIMIT 1
                """, (email,))
                sub_result = cursor.fetchone()
                if sub_result:
                    # 允许以邮箱为用户名免密登录
                    conn.close()
                    return {
                        "user_name": sub_result[0] or email, 
                        "user_email": sub_result[1], 
                        "is_admin": False
                    }
        except Exception as e:
            st.error(f"登录验证失败: {e}")
        finally:
            conn.close()
    return None

def is_admin(user_email):
    """Check if the user is admin"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM admin_users WHERE email = ?", (user_email,))
            result = cursor.fetchone()
            return result is not None
        except:
            return False
        finally:
            conn.close()
    return False

def get_user_subscriptions(user_email):
    """Get user's current subscriptions from database"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT interested_tag FROM subscriptions WHERE user_email = ?
            """, (user_email,))
            subscriptions = [row[0] for row in cursor.fetchall()]
            return subscriptions
        except Exception as e:
            st.error(f"获取订阅失败: {e}")
            return []
        finally:
            conn.close()
    return []

def update_user_subscriptions(user_email, user_name, selected_tags):
    """Update user's subscriptions in database"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # 先删除当前用户的所有订阅
            cursor.execute("DELETE FROM subscriptions WHERE user_email = ?", (user_email,))
            
            # 添加新的订阅
            for tag in selected_tags:
                cursor.execute("""
                    INSERT INTO subscriptions (user_name, user_email, interested_tag) VALUES (?, ?, ?)
                """, (user_name, user_email, tag))
            
            conn.commit()
            return True, "订阅更新成功！"
        except Exception as e:
            st.error(f"更新订阅失败: {e}")
            return False, f"更新订阅失败: {e}"
        finally:
            conn.close()
    return False, "数据库连接失败"


# --- 用户认证状态管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# 初始化分析表和用户表（如果不存在）
init_analysis_table()
init_users_table()
init_subscriptions_table()

# --- 主界面 ---
st.title("📡 AI 智能情报分析门户")

# 显示登录状态和登出按钮
if st.session_state.logged_in:
    st.sidebar.success(f"欢迎, {st.session_state.user_name}")
    col_logout, col_refresh = st.sidebar.columns(2)
    with col_logout:
        if st.button("登出"):
            st.session_state.logged_in = False
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.is_admin = False
            st.rerun()
    with col_refresh:
        if st.button("🔄 刷新"):
            st.rerun()

# 登录/注册区域
if not st.session_state.logged_in:
    with st.expander("🔐 用户登录", expanded=True):
        login_tab, register_tab = st.tabs(["登录", "注册"])
        
        with login_tab:
            st.subheader("登录")
            login_email = st.text_input("邮箱", key="login_email")
            login_password = st.text_input("密码", type="password", key="login_password")
            
            if st.button("登录", type="primary"):
                with st.spinner("正在验证登录信息..."):
                    user = login_user(login_email, login_password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user_email = user["user_email"]
                        st.session_state.user_name = user["user_name"]
                        st.session_state.is_admin = user["is_admin"]
                        st.success("登录成功！")
                        st.rerun()
                    else:
                        st.error("登录失败：邮箱不存在或密码错误")
        
        with register_tab:
            st.subheader("注册")
            reg_name = st.text_input("姓名", key="reg_name")
            reg_email = st.text_input("邮箱", key="reg_email")
            reg_password = st.text_input("密码", type="password", key="reg_password")
            reg_confirm_password = st.text_input("确认密码", type="password", key="reg_confirm_password")
            
            if st.button("注册", type="primary"):
                if not reg_name or not reg_email or not reg_password:
                    st.error("请填写所有字段")
                elif reg_password != reg_confirm_password:
                    st.error("两次输入的密码不一致")
                else:
                    with st.spinner("正在注册..."):
                        success, msg = register_user(reg_name, reg_email, reg_password)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)

# --- 订阅管理 ---
if st.session_state.logged_in:
    with st.expander("📋 订阅管理", expanded=True):
        st.subheader(f"订阅新闻领域 - {st.session_state.user_name}")
        
        # 获取所有可用的新闻标签
        conn = get_db_connection()
        available_tags = []
        if conn:
            try:
                # 获取所有不同的标签
                tags_df = pd.read_sql("SELECT DISTINCT tag FROM reports", conn)
                available_tags = [row['tag'] for row in tags_df.to_dict('records')]
            except:
                st.warning("暂无可用新闻标签")
            finally:
                conn.close()
        
        # 如果没有可用标签，提供一些示例
        if not available_tags:
            available_tags = ['世界时事', '科技前沿', '财经资讯', '健康生活', '体育赛事', '澳门', '军事']
        
        # 获取当前用户的订阅
        current_subscriptions = get_user_subscriptions(st.session_state.user_email)
        
        # 管理员用户默认订阅所有领域
        if st.session_state.is_admin:
            selected_tags = st.multiselect(
                "选择您感兴趣的新闻领域",
                options=available_tags,
                default=available_tags  # 管理员默认选择全部
            )
        else:
            # 普通用户显示当前订阅
            selected_tags = st.multiselect(
                "选择您感兴趣的新闻领域",
                options=available_tags,
                default=current_subscriptions
            )
        
        if st.button("更新订阅", type="primary"):
            with st.spinner("正在更新订阅..."):
                success, msg = update_user_subscriptions(
                    st.session_state.user_email, 
                    st.session_state.user_name, 
                    selected_tags
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

# --- 世界时事日报展示 ---
st.markdown("---")
st.header("🌍 世界时事日报")

# 显示世界时事相关的报告
conn = get_db_connection()
if conn:
    try:
        # 获取最新的世界时事报告
        world_news_df = pd.read_sql(
            "SELECT tag, html_content, time, created_at FROM reports WHERE tag LIKE '%世界%' OR tag LIKE '%国际%' OR tag LIKE '%时事%' ORDER BY created_at DESC LIMIT 10",
            conn
        )
        
        if not world_news_df.empty:
            # 选择特定日期的报告
            report_options = [f"{row['time']} - {row['tag']}" for _, row in world_news_df.iterrows()]
            selected_report = st.selectbox("选择世界时事报告", report_options)
            
            # 找到选定的报告
            selected_idx = report_options.index(selected_report)
            selected_row = world_news_df.iloc[selected_idx]
            
            # 清洗并显示内容
            cleaned_content = clean_html_content(selected_row['html_content'])
            st.markdown("---")
            components.html(cleaned_content, height=800, scrolling=True)
        else:
            st.info("暂无世界时事相关报告。")
    except Exception as e:
        st.error(f"读取世界时事报告失败: {e}")
    finally:
        if conn:
            conn.close()

# 仅对已登录用户显示其他报告
if st.session_state.logged_in:
    st.markdown("---")
    st.header("📰 个性化新闻报告")
    
    # 获取用户订阅的标签
    user_subscriptions = get_user_subscriptions(st.session_state.user_email)
    
    if user_subscriptions:
        conn = get_db_connection()
        if conn:
            try:
                # 构建SQL查询，只显示用户订阅的新闻标签
                placeholders = ','.join(['?' for _ in user_subscriptions])
                query = f"""
                    SELECT DISTINCT tag, MAX(created_at) as latest_created_at 
                    FROM reports 
                    WHERE tag IN ({placeholders}) 
                    GROUP BY tag 
                    ORDER BY latest_created_at DESC
                """
                
                other_reports_df = pd.read_sql(query, conn, params=user_subscriptions)
                
                if not other_reports_df.empty:
                    # 显示可选的标签
                    other_tags = [row['tag'] for _, row in other_reports_df.iterrows()]
                    selected_other_tag = st.selectbox("选择新闻领域", other_tags)
                    
                    # 获取选定标签的最新报告
                    latest_report_df = pd.read_sql(
                        "SELECT html_content, time, created_at FROM reports WHERE tag = ? ORDER BY created_at DESC LIMIT 1",
                        conn,
                        params=(selected_other_tag,)
                    )
                    
                    if not latest_report_df.empty:
                        latest_report = latest_report_df.iloc[0]
                        cleaned_content = clean_html_content(latest_report['html_content'])
                        st.markdown("---")
                        components.html(cleaned_content, height=800, scrolling=True)
                else:
                    st.info("暂无订阅领域的新闻报告。")
            except Exception as e:
                st.error(f"读取个性化报告失败: {e}")
            finally:
                if conn:
                    conn.close()
    else:
        st.info("您还没有订阅任何新闻领域，请前往订阅管理设置感兴趣的主题。")

# --- 管理员才能看到的系统实时监控 ---
if st.session_state.is_admin:
    st.sidebar.title("📊 系统实时监控")
    conn = get_db_connection()

    if conn:
        try:
            # 检查表是否存在
            tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
            if 'news_raw' in tables.values:
                # 使用横向表格显示状态统计
                status_df = pd.read_sql("SELECT status as '状态', COUNT(*) as '数量' FROM news_raw GROUP BY status", conn)
                st.sidebar.subheader("新闻状态统计")
                st.sidebar.table(status_df)
                
                source_df = pd.read_sql("SELECT source as '来源', COUNT(*) as '条数' FROM news_raw GROUP BY source", conn)
                st.sidebar.subheader("新闻来源统计")
                st.sidebar.bar_chart(source_df.set_index('来源'))
            else:
                st.sidebar.warning("等待数据入库...")
        except Exception as e:
            st.sidebar.error(f"监控数据读取失败: {e}")

# --- 管理员才能看到的原始数据流水 ---
if st.session_state.is_admin:
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
else:
    # 非管理员用户仍然可以看到深度日报预览
    st.markdown("---")
    st.header("📅 深度日报预览")
    conn = get_db_connection()
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

# 逻辑优化：确保在页面结束前关闭连接
if 'conn' in locals() and conn:
    conn.close()

# --- 页脚 ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888;'>
        <p>📡 AI 智能情报分析门户 | 数据实时更新中</p>
    </div>
    """,
    unsafe_allow_html=True
)