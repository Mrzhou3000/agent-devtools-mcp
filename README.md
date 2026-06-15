<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/MCP-DevTools_%7C_DBTools_%7C_KB_Tools-5B5BD6?style=for-the-badge&logo=python&logoColor=white">
    <img alt="Agent DevTools MCP" src="https://img.shields.io/badge/MCP-DevTools_%7C_DBTools_%7C_KB_Tools-5B5BD6?style=for-the-badge&logo=python&logoColor=white">
  </picture>
</p>

<p align="center">
  <em>生产级 MCP 工具网关套件 —— 为 AI Agent 提供开发工具 / 数据库 / 知识库<br>三大领域的安全可控调用能力</em>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python" alt="Python 3.12+"></a>
  <a href="#"><img src="https://img.shields.io/badge/MCP-1.0%2B-5B5BD6" alt="MCP 1.0+"></a>
  <a href=".github/workflows/ci.yml"><img src="https://img.shields.io/badge/CI-Ruff%20%7C%20mypy%20%7C%20pytest-success" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
</p>

---

## 目录

- [什么是 Agent DevTools MCP？](#什么是-agent-devtools-mcp)
- [架构概览](#架构概览)
- [三大模块](#三大模块)
  - [mcp-devtools —— 开发工具](#mcp-devtools--开发工具)
  - [mcp-dbtools —— 数据库查询](#mcp-dbtools--数据库查询)
  - [mcp-kbtools —— 知识库搜索](#mcp-kbtools--知识库搜索)
- [安全设计（三层纵深防御）](#安全设计三层纵深防御)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [部署](#部署)
- [配套项目](#配套项目)
- [License](#license)

---

## 什么是 Agent DevTools MCP？

Agent DevTools MCP 是一套**开箱即用的 MCP Server 工具集**，专为 AI Agent（Claude、GPT 等）设计。它把开发者日常使用的**文件操作、命令执行、Git 查询、数据库查询、语义搜索**等能力封装成标准的 MCP 工具，让 AI 助手可以安全可控地调用。

**三大核心价值：**

| | 价值 | 解决什么问题 |
|:--|:------|:------------|
| 🛡️ | **纵深安全防御** | 三层防线保障 AI 不会误操作生产环境 |
| 🧩 | **标准 MCP 协议** | 兼容所有 MCP 客户端（Claude Desktop、VS Code、JetBrains 等） |
| 🏗️ | **生产级工程化** | 完整 CI/CD、测试覆盖、Docker 支持、PyPI 发布 |

## 架构概览

```
┌────────────────────────────────────────────────────────────┐
│                     MCP 协议层                              │
│   Stdio 传输 ←→ JSON-RPC ←→ 所有标准 MCP 客户端             │
└──────────┬───────────┬───────────┬─────────────────────────┘
           │           │           │
     ┌─────▼─────┐ ┌──▼────┐ ┌───▼──────┐
     │ devtools  │ │dbtools│ │ kbtools  │  ← 三个独立 MCP Server
     │  MCP Srv  │ │MCP Srv│ │ MCP Srv  │    （可单独或一起启动）
     └─────┬─────┘ └──┬────┘ └───┬──────┘
           │           │          │
           └───────────┼──────────┘
                       │
            ┌──────────▼──────────┐
            │    mcp-common       │  ← 公共基础库（所有模块共用）
            │  ┌────────────────┐ │
            │  │ 安全模块        │ │  ← 命令验证 / 路径防护 / SQL 校验
            │  │ 日志模块        │ │  ← 结构化日志 + Trace ID
            │  │ 错误码模块      │ │  ← 统一错误分类与处理
            │  │ 配置管理        │ │  ← 环境变量 + YAML 配置
            │  │ 拦截器链        │ │  ← 日志 / 审计 / 限流
            │  └────────────────┘ │
            └─────────────────────┘
```

## 三大模块

### mcp-devtools —— 开发工具

面向 AI Agent 的文件操作与命令执行能力，适合代码审查、项目分析等场景。

| 工具 | 功能 | 安全约束 |
|:-----|:-----|:---------|
| `read_file` | 读取文件内容 | 仅限工作区内、纯文本文件 |
| `write_file` | 写入文件 | 默认关闭，需显式配置 |
| `list_directory` | 列出目录结构 | 仅限工作区内 |
| `run_command` | 执行 Shell 命令 | 命令白名单、默认关闭 |
| `run_git_command` | 执行 Git 查询 | 只读 Git 命令 |

### mcp-dbtools —— 数据库查询

为 AI Agent 提供数据库查询能力，支持只读查询、表结构探查、结果分页。

| 工具 | 功能 | 安全约束 |
|:-----|:-----|:---------|
| `query` | 执行只读 SQL | AST 级 SQL 解析，拒绝写操作 |
| `list_tables` | 列出所有表 | — |
| `describe_table` | 查看表结构 | — |
| `query_with_pagination` | 分页查询 | — |

**数据库支持：** SQLite（内置）、PostgreSQL（适配器模式，扩展其他数据库只需实现一个类）。

### mcp-kbtools —— 知识库搜索

为 AI Agent 提供本地文档索引与语义搜索能力，适合项目知识库、技术文档检索。

| 工具 | 功能 | 说明 |
|:-----|:-----|:-----|
| `create_knowledge_base` | 创建知识库 | 支持配置 Embedding 模型 |
| `index_documents` | 索引文档 | 自动分块、去重 |
| `search_knowledge_base` | 搜索知识库 | BM25 全文检索（默认）或向量语义搜索 |

## 安全设计（三层纵深防御）

本项目最核心的设计亮点——**三层纵深防御体系**：

```
第1层：边界防护  ──→ 工作区隔离 + 命令白名单
第2层：操作管控  ──→ 路径校验 + 注入防护 + SQL AST 只读校验
第3层：审计追溯  ──→ 审计日志 + Trace ID 透传
```

| 层级 | 防护机制 | 实现方式 |
|:-----|:---------|:---------|
| **边界** | 工作区隔离 | 所有文件操作限制在指定工作目录内 |
| **边界** | 命令白名单 | 只允许预设的命令被执行 |
| **操作** | 路径穿越防护 | `Path.resolve()` 规范化，拒绝 `..` 路径 |
| **操作** | 命令注入防护 | 全程 `shell=False`，参数检测危险字符 |
| **操作** | SQL 只读校验 | **AST 级 SQL 解析**（基于 sqlglot），非正则——不可绕过 |
| **操作** | 输出大小限制 | 最大 1MB / 5000 行 |
| **操作** | 超时控制 | 命令 / 查询超时自动终止 |
| **审计** | 审计日志 | 每次工具调用记录（谁 / 何时 / 调用了什么） |
| **审计** | Trace ID | 每个请求唯一 ID，贯穿调用链路 |
| **审计** | 脱敏记录 | 审计日志不记录完整文件内容 |

**设计原则：** 默认拒绝、纵深防御、最小权限。

> 💡 大多数类似项目只是简单封装 shell 命令，没有任何安全防护。本项目的安全设计是面试的**最大亮点**。

## 快速开始

### 前置条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)（包管理器，提供 workspace 支持）

```bash
# 安装 uv
pip install uv

# 克隆项目
git clone https://github.com/Mrzhou3000/agent-devtools-mcp.git
cd agent-devtools-mcp

# 安装所有依赖（含可选依赖）
uv sync --all-extras
```

### 启动 MCP Server

每个模块可以独立启动：

```bash
# 开发工具 —— 需要使用文件和命令
uv run --package mcp-devtools mcp-devtools run --workspace .

# 数据库查询 —— 需要指定数据库文件
uv run --package mcp-dbtools mcp-dbtools run --database ./test.db

# 知识库搜索
uv run --package mcp-kbtools mcp-kbtools run
```

### 配置 Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "devtools": {
      "command": "uv",
      "args": [
        "run", "--package", "mcp-devtools",
        "python", "-m", "mcp_devtools", "run",
        "--workspace", "."
      ]
    },
    "dbtools": {
      "command": "uv",
      "args": [
        "run", "--package", "mcp-dbtools",
        "python", "-m", "mcp_dbtools", "run",
        "--database", "./test.db"
      ]
    },
    "kbtools": {
      "command": "uv",
      "args": [
        "run", "--package", "mcp-kbtools",
        "python", "-m", "mcp_kbtools", "run"
      ]
    }
  }
}
```

## 项目结构

```
agent-devtools-mcp/
├── pyproject.toml              # 根工作空间（uv workspace）
├── .github/workflows/          # CI/CD 配置
│   ├── ci.yml                  # 代码检查 + 全平台测试
│   └── release.yml             # PyPI 发布
├── packages/
│   ├── mcp-common/             # 公共基础库
│   │   ├── src/mcp_common/
│   │   │   ├── security/       # 安全模块（命令/路径/SQL 校验）
│   │   │   ├── logging/        # 结构化日志 + Trace ID
│   │   │   ├── middleware/     # 拦截器链
│   │   │   ├── config/         # 配置管理
│   │   │   └── errors/         # 统一错误码
│   │   └── tests/              # 8 个测试文件，54 个 AST SQL 测试
│   ├── mcp-devtools/           # 开发工具 MCP Server
│   │   ├── src/mcp_devtools/
│   │   │   └── tools/          # read_file / run_command / git 等
│   │   └── tests/
│   ├── mcp-dbtools/            # 数据库查询 MCP Server
│   │   ├── src/mcp_dbtools/
│   │   │   ├── adapters/       # SQLiteAdapter / PostgreSQLAdapter
│   │   │   └── tools/          # query / list_tables 等
│   │   └── tests/
│   └── mcp-kbtools/            # 知识库搜索 MCP Server
│       ├── src/mcp_kbtools/
│       │   ├── ingestion/      # 文档加载 + 分块
│       │   ├── retrieval/      # BM25 搜索（+可插拔向量搜索）
│       │   └── tools/          # create / index / search
│       └── tests/
├── docs/                       # 设计文档
│   ├── architecture.md
│   ├── security.md
│   └── deployment.md
├── integration_tests/          # 跨模块集成测试
├── examples/                   # 配置示例
├── Dockerfile                  # 容器化部署
└── Makefile                    # 常用命令快捷入口
```

## 开发指南

```bash
# 安装开发依赖
make dev

# 运行全部测试
make test                    # pytest -v
make test-coverage           # pytest + 覆盖率报告
make test-quick              # 快速模式（失败即停）

# 代码质量
make lint                    # Ruff 代码检查
make format                  # Ruff 自动格式化
make typecheck               # mypy 严格模式类型检查
make all                     # format → lint → typecheck → test

# 预提交检查（安装后每次 git commit 自动运行）
pip install pre-commit && pre-commit install
```

## 部署

### Docker

```bash
docker build -t agent-devtools-mcp .
docker run -v /path/to/workspace:/workspace agent-devtools-mcp \
    mcp-devtools python -m mcp_devtools run --workspace /workspace
```

### PyPI 安装

```bash
# 安装特定模块
pip install mcp-devtools
pip install mcp-dbtools
pip install mcp-kbtools
```

## 配套项目

| 项目 | 说明 | 链接 |
|:-----|:-----|:------|
| **Agent-CLI** | MCP Client 端 —— 在终端中与 MCP Server 交互的 CLI 工具 | [GitHub](https://github.com/Mrzhou3000/agent-cli) |

本项目为 MCP **Server** 端（提供工具），Agent-CLI 为 MCP **Client** 端（消费工具）。两者配合使用，形成对 MCP 协议请求和响应两端的完整理解。

## License

[MIT](LICENSE) © 2026 Mrzhou3000
