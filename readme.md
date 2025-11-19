# Deep Research Graph (Pro) - AI 科研助手

这是一个专为 AI/CS 领域研究人员打造的深度科研辅助平台。它集成了 Zotero 知识库管理、ArXiv 实时情报雷达、学术引用图谱分析以及基于 Gemini 1.5 的全文本深度研读功能。

## ✨ 核心功能

### 📚 Zotero 深度集成
*   **全量同步**：自动分页抓取您 Zotero 库中的所有文献，过滤非论文条目（附件、笔记）。
*   **本地缓存**：首次同步后建立本地索引，实现秒级启动。
*   **用户画像**：自动分析您的收藏偏好，提取高频科研关键词。

### 📡 ArXiv 智能雷达
*   **个性化推荐**：摒弃传统的关键词订阅，系统会根据您的 Zotero 画像，自动在 ArXiv 过去 24 小时的最新论文中筛选高相关度内容。
*   **一键研读**：感兴趣的论文可直接推送到深度研读模式。

### 🕸️ 知识图谱与路径规划
*   **引用网络可视化**：基于 Semantic Scholar 数据构建引用关系网，区分“基石文献”（Reference）和“后续发展”（Citation）。
*   **智能学习路径**：利用 PageRank 算法 + LLM 分析，为您规划“必读路径”，不再迷失在文献海中。

### 🤖 Gemini 全文深度研读
*   **多模态阅读**：自动下载 ArXiv PDF，上传至 Gemini 1.5 Pro/Flash 模型。
*   **沉浸式对话**：支持针对论文全文（包含公式、图表）的深度问答，而非仅仅基于摘要。

## 🛠️ 环境要求

*   **Python 3.10+** (强烈推荐，以兼容 Google GenAI SDK)
*   **科学的上网环境** (用于访问 Google Gemini, ArXiv, Semantic Scholar)

## 🚀 快速开始

**1. 安装依赖**

```bash
pip install -r requirements.txt
```

**2. 启动应用**

```bash
streamlit run webui.py
```

## ⚙️ 配置指南

启动应用后，请在左侧边栏的 **“控制台”** 中完成以下配置。配置会自动保存到本地 `config.yaml`。

### 1. 基础模型 (必填)
*   **OpenAI / DeepSeek Key**: 用于生成引用图谱推荐、分析摘要。
*   **Base URL**: 如果使用 DeepSeek，填 `https://api.deepseek.com`。
*   **Model**: 例如 `deepseek-chat` 或 `gpt-4-turbo`。

### 2. 全文研读模型 (必填)
*   **Gemini Key**: 用于阅读 PDF 全文。[申请地址](https://aistudio.google.com/app/apikey)
*   **Model**: 推荐 `gemini-1.5-flash` (速度快、免费额度高) 或 `gemini-1.5-pro` (推理能力更强)。

### 3. Zotero 同步 (必填)
*   **User ID & API Key**: 用于同步您的文献库。[获取地址](https://www.zotero.org/settings/keys)

### 4. 学术数据源 (选填)
*   **Semantic Scholar Key**: 用于构建引用图谱。
    *   *注：不填也能用，但会有频率限制（每5分钟约100次请求）。*

## 📂 项目结构

```text
.
├── main.py             # 核心配置管理与数据模型
├── webui.py            # Streamlit 前端界面主入口
├── zotero_sync.py      # Zotero 同步逻辑 (含自动重试与缓存)
├── graph_engine.py     # 引用图谱构建与 LLM 路径分析引擎
├── pdf_manager.py      # ArXiv PDF 自动下载与管理
├── gemini_client.py    # Google Gemini SDK 封装 (含文件上传)
├── config.yaml         # 自动生成的配置文件 (勿提交到 git)
└── zotero_cache.json   # Zotero 本地缓存数据
```

## ❓ 常见问题 (Troubleshooting)

**Q: 启动时报错 `importlib.metadata...`？**
> **A:** 您的 Python 版本过低。请升级到 Python 3.10 或以上。

**Q: Zotero 同步失败 `ProxyError`？**
> **A:** 代码已内置自动降级机制。如果检测到代理错误，会自动尝试直连。请确保您的网络环境正常。

**Q: Gemini 报错 `404 Not Found`？**
> **A:** 请检查模型名称是否正确。推荐使用 `gemini-1.5-flash`。部分旧 Key 可能无法访问 Pro 模型。

**Q: PDF 下载失败？**
> **A:** ArXiv 有反爬限制。代码中已伪装 User-Agent，但如果请求过于频繁仍可能被封。稍后重试即可。

---