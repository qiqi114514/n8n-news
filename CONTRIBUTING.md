# 贡献指南

感谢您有兴趣为 n8n-news 项目做出贡献！本文档提供了参与开发所需的所有信息。

## 📋 开发环境设置

1. Fork 仓库到您的账户
2. 克隆项目到本地
   ```bash
   git clone https://github.com/yourusername/n8n-news.git
   cd n8n-news
   ```
3. 创建虚拟环境并安装依赖
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. 创建特性分支进行开发
   ```bash
   git checkout -b feature/AmazingFeature
   ```

## 🧪 测试

在提交更改之前，请确保测试通过：

```bash
# 运行测试套件
python -m pytest tests/
```

## 📝 提交更改

1. 提交您的更改
   ```bash
   git add .
   git commit -m 'Add some AmazingFeature'
   ```
2. 推送到分支
   ```bash
   git push origin feature/AmazingFeature
   ```
3. 创建 Pull Request

## 🚩 代码规范

- 使用 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 代码风格
- 编写有意义的提交消息
- 添加适当的注释和文档字符串
- 确保代码兼容 Python 3.11+

## 🐛 报告 Bug

如果您发现 bug，请在 Issues 中报告。请包括：

- 您使用的版本
- 重现步骤
- 预期行为
- 实际行为

## 💡 建议新功能

我们欢迎功能建议！请清楚地描述功能并解释它如何使项目受益。

## 🤝 社区

如有任何疑问，请随时在 Issues 中提问。

## 📄 许可证

通过参与此项目，您同意遵守项目许可证。