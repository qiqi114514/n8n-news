# n8n-news - 新闻智能采集与分析系统

这是一个基于Python开发的新闻智能采集与分析系统，能够从多个国际新闻源抓取新闻数据，并通过n8n进行智能化分析处理。

## 🚀 功能特点

- **多源新闻采集**: 支持AP News、BBC、CCTV、ChinaNews等多个国际新闻源
- **智能数据分析**: 结合n8n工作流引擎实现新闻数据的自动化处理与分析
- **可视化展示**: 提供Streamlit界面实时查看新闻数据与分析结果
- **容器化部署**: 使用Docker和Docker Compose简化部署流程

## 📋 依赖环境

- Python 3.11+
- Docker & Docker Compose
- SQLite (用于数据存储)

## 🛠️ 快速开始

### 使用Docker Compose启动服务

```bash
# 克隆项目
git clone <repository-url>
cd n8n-news

# 启动服务
docker-compose up -d
```

### 手动安装运行

```bash
# 安装依赖
pip install -r src/requirements.txt

# 运行爬虫
python src/runner.py

# 启动Web界面
streamlit run src/app.py
```

## 🔧 项目结构

```
n8n-news/
├── src/                    # 源代码目录
│   ├── crawlers/           # 各新闻源爬虫实现
│   ├── api_server.py       # API服务器
│   ├── app.py              # Streamlit应用
│   ├── config.py           # 项目配置
│   ├── scheduler.py        # 任务调度器
│   └── ...
├── data/                   # 数据存储目录
├── logs/                   # 日志目录
├── Dockerfile             # Docker镜像构建文件
├── docker-compose.yml     # Docker Compose配置
└── README.md
```

## 🌐 支持的新闻源

- AP News
- BBC
- CCTV
- Xinhua (新华社)
- ChinaNews (中新网)
- People (人民网)
- Reuters
- NHK (日本)
- France24 (法语)
- Guardian (卫报)

## 📊 数据处理流程

1. **数据采集**: 各爬虫模块定时从新闻源抓取最新资讯
2. **数据入库**: 将原始数据存储至SQLite数据库
3. **智能分析**: 通过n8n工作流对数据进行AI分析
4. **结果展示**: 在Streamlit界面中展示分析结果

## ⚙️ 配置说明

修改 [src/config.py](./src/config.py) 可以调整以下参数：
- 请求头配置
- 超时时间设置
- 日志级别配置
- 最大新闻条数限制

## 🚦 服务端口

- Streamlit界面: `https://reattach-epilogue-trustable.ngrok-free.dev/`

## 🤝 贡献

欢迎提交Issue和Pull Request来帮助改进此项目。

## 📄 许可证

本项目采用 [LICENSE](./LICENSE) 许可证。