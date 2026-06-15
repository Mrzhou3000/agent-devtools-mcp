# Agent DevTools MCP — 开发规范文档

> **项目名称**: Agent DevTools MCP  
> **版本**: v1.0.0 (规划)  
> **最后更新**: 2026-06-15  
> **项目定位**: 生产级 MCP 工具网关套件，为 AI Agent 提供开发工具/数据库/知识库三大领域的安全可控调用能力  
> **配套项目**: [Agent-CLI](https://github.com/Mrzhou3000/agent-cli) — MCP Client 端

---

## 📑 目录

1. [写给初学者的话](#1-写给初学者的话)
2. [项目概述与定位](#2-项目概述与定位)
3. [技术选型与设计哲学](#3-技术选型与设计哲学)
4. [系统架构（核心决策）](#4-系统架构核心决策)
5. [三大模块详解](#5-三大模块详解)
6. [三层纵深安全防御体系](#6-三层纵深安全防御体系)
7. [统一工程化规范](#7-统一工程化规范)
8. [测试规范](#8-测试规范)
9. [部署与运行方案](#9-部署与运行方案)
10. [开发路线图（三阶段）](#10-开发路线图三阶段)
11. [面试指南](#11-面试指南)
12. [初学者学习路径](#12-初学者学习路径)

---

## 1. 写给初学者的话

> ⚠️ **如果你之前没做过完整的 Python 项目，请先读这一节。**

### 1.1 这个项目会教你什么

| 技能 | 学到什么程度 | 对求职的帮助 |
|:-----|:-----------|:------------|
| **Python 项目结构** | 多包工作空间、src 布局、依赖管理 | 面试常问"你的项目怎么组织的" |
| **MCP 协议** | 服务端实现（不是只会调 API） | 2025-2026 最热门的 AI 协议 |
| **安全编程** | 命令注入防护、路径穿越防护、SQL 注入防护 | **拉开你和其他求职者的关键差距** |
| **生产级工程化** | CI/CD、测试覆盖、Docker、PyPI 发布 | 面试官最看重的"能不能直接干活" |
| **架构设计** | 分层架构、策略模式、工厂模式 | 从"写代码"到"设计系统"的跨越 |

### 1.2 你需要具备的基础

- ✅ Python 基础语法（变量、函数、类、列表推导式）
- ✅ 会用 pip 安装包，知道虚拟环境（venv/uv）
- ✅ 写过简单的 Python 脚本或小工具
- ✅ 了解 Git 基本操作（add/commit/push）
- ⚠️ **不需要**：之前做过 MCP 项目（这个项目就是教你做）

### 1.3 你需要安装的工具

| 工具 | 用途 | 安装方式 |
|:-----|:-----|:---------|
| **Python 3.12+** | 运行环境 | [python.org](https://python.org) 下载 |
| **uv** | Python 包管理和工作空间管理 | `pip install uv` 或 `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Git** | 版本控制 | `apt install git` 或 [git-scm.com](https://git-scm.com) |
| **GitHub CLI (gh)** | 创建 PR、管理仓库 | `apt install gh` 或 `brew install gh` |
| **Docker**（可选） | 容器化部署 | [docker.com](https://docker.com) |

> **什么是 uv？** uv 是 Rust 写的 Python 包管理器，比 pip 快 10-100 倍。它支持**工作空间（workspace）**功能——我们这个多包项目正好需要。你只需要记 3 个命令：
> - `uv sync` — 安装所有依赖（相当于 `pip install -r requirements.txt`）
> - `uv run <命令>` — 在虚拟环境中运行命令
> - `uv add <包名>` — 添加依赖

### 1.4 本文档的阅读方法

- **📖 必须读的章节**：第 2-6 章（决定项目能否开工）
- **🔧 开发时参考的章节**：第 5 章（每个工具的详细规范）
- **🎯 面试前准备的章节**：第 7、10、11 章（工程化和面试话术）
- **📚 遇到不懂的概念时看**：第 12 章（学习路径）

---

## 2. 项目概述与定位

### 2.1 这个项目解决什么问题？

AI Agent（比如 Claude、GPT）的能力取决于它能调用什么**工具**。MCP (Model Context Protocol) 是 AI 模型调用工具的标准协议。

**本项目做的事情：** 把开发者常用的工具（文件操作、命令行、Git、数据库查询、文档搜索）封装成标准的 MCP 工具，让 AI Agent 可以安全地调用。

**核心痛点：**
| 痛点 | 市场上大多数方案 | 我们的方案 |
|:-----|:----------------|:-----------|
| 安全风险 | 直接封装 shell 命令，没有任何防护 | 三层纵深防御体系 |
| 工程化差 | 零散的 Python 脚本，没有测试 | 完整工程化（测试/CI/CD/Docker） |
| 生态不兼容 | 自定义协议，只能配合特定客户端 | 标准 MCP 协议，兼容所有客户端 |

### 2.2 项目两大核心价值

```
① 体系化的安全设计（面试最大亮点）
   ┌─────────────────────────────────────────────┐
   │ 大多数求职者："我的项目调了 OpenAI API"    │
   │ 你： "我设计了三层安全防御体系，包括……"     │
   │    面试官： 👀 这人有点东西                   │
   └─────────────────────────────────────────────┘

② 完整理解 MCP 协议两端（与其他项目形成闭环）
   配套项目 Agent-CLI = MCP Client（消费端）
   本项目 = MCP Server（提供端）
   → "我完整理解 MCP 协议的请求和响应两端"
```

### 2.3 与 Agent-CLI（1 号项目）的关系

```
Agent-CLI (#1)                         Agent DevTools MCP (#2)
══════════════                         ═══════════════════════════
MCP Client 端                           MCP Server 端
(消费 MCP 服务)                          (提供 MCP 服务)
                                        ┌──────────────────────┐
  Agent 决定调用工具 ── MCP 协议 ────→ │  mcp-devtools        │
                           JSON-RPC    │  (文件/命令/Git)       │
                                        ├──────────────────────┤
                                        │  mcp-dbtools         │
                                        │  (数据库查询)         │
                                        ├──────────────────────┤
                                        │  mcp-kbtools         │
                                        │  (知识库搜索)         │
                                        └──────────────────────┘
```

---

## 3. 技术选型与设计哲学

### 3.1 技术栈

| 层面 | 选型 | 为什么选它 |
|:-----|:-----|:-----------|
| **语言** | Python 3.12+ | Agent 开发岗位 73% 要求 Python（2026 招聘数据） |
| **MCP SDK** | `mcp` (官方) | Anthropic 维护，社区标准 |
| **CLI 框架** | Typer | 类型安全，自动生成 --help |
| **包管理** | uv | 比 pip 快 10-100 倍，原生支持工作空间 |
| **数据库** | SQLite | 零配置，本地开发即用 |
| **知识库索引** | Whoosh (BM25) | 纯 Python 实现，零外部依赖 |
| **Embedding** | sentence-transformers (可选) | 需要时再装，渐进复杂 |
| **测试** | pytest + pytest-cov | Python 测试标准 |
| **CI/CD** | GitHub Actions | 业界标准 |
| **部署** | PyPI + Docker | 包管理 + 容器化双通道 |
| **代码质量** | Ruff + mypy | 与 1 号项目保持一致 |

### 3.2 设计原则

```
① 安全优先 ──→ 默认拒绝，配置放行
   所有写入操作默认禁用，需要用户显式配置才开启
   
② 渐进复杂 ──→ 核心功能简单，高级功能可选
   基础搜索（BM25）开箱即用，向量搜索按需安装

③ 可观测 ──→ 每次调用都可追踪
   所有工具调用记录日志，带唯一 Trace ID

④ 防御性 ──→ 永远假设输入是恶意的
   每个参数都校验，不做信任假设
```

### 3.3 设计模式使用

| 模式 | 用在哪里 | 为什么用 |
|:-----|:---------|:---------|
| **策略模式 + 工厂模式** | 数据库适配器 | 方便扩展新的数据库类型（加一个类就行） |
| **模板方法模式** | 工具实现基类 | 统一所有工具的调用流程（校验 → 执行 → 返回） |
| **拦截器模式** | 通用能力层 | 日志、鉴权、限流等横切关注点统一处理 |
| **适配器模式** | 数据库/知识库存储 | 屏蔽底层实现差异（SQLite vs PostgreSQL / Whoosh vs Chroma） |

> **对面试官说：** *"我在项目里用了策略模式来抽象数据库适配器，这样加新数据库只需要实现一个类，不用改业务代码。"*

---

## 4. 系统架构（核心决策）

### 4.1 整体架构：统一底座 + 领域模块

这是本项目**最重要的架构决策**。我们采用多包单体仓（Monorepo）结构：

```
┌──────────────────────────────────────────────────────────────────┐
│                        MCP 协议层                                │
│   Stdio 传输 ←→ JSON-RPC ←→ 所有标准 MCP 客户端                  │
└──────────┬──────────┬──────────┬────────────────────────────────┘
           │          │          │
     ┌─────▼────┐ ┌──▼───┐ ┌───▼────┐
     │ devtools │ │dbtool│ │ kbtool │  ← 三个独立 MCP Server
     │  MCP Srv │ │MCP Sr│ │ MCP Sr │    （可单独启动）
     └─────┬────┘ └──┬───┘ └───┬────┘
           │          │          │
           └──────────┼──────────┘
                      │
           ┌──────────▼──────────┐
           │    mcp-common       │  ← 公共基础库（所有模块共用）
           │  ┌────────────────┐ │
           │  │ 安全模块        │ │  ← 三层防御体系
           │  │ 日志模块        │ │  ← 结构化日志 + Trace ID
           │  │ 错误码模块      │ │  ← 统一错误格式
           │  │ 配置管理        │ │  ← 环境变量 + 配置文件
           │  │ 拦截器链        │ │  ← 鉴权/限流/审计
           │  └────────────────┘ │
           └─────────────────────┘
```

### 4.2 为什么选多包而不是单体？

| 维度 | 单体方案 | 多包方案（我们选这个） |
|:-----|:---------|:---------------------|
| **代码组织** | 一个项目，文件夹分区 | 四个独立小项目，各管各的 |
| **依赖管理** | 所有依赖在一个 `pyproject.toml` | 每个模块有自己的依赖（公共的放 common） |
| **启动方式** | 一个 Server 启动所有功能 | 三个 Server 各自启动 |
| **面试展示** | "我写了一个大项目" | "我设计了可复用的架构，这是架构抽象能力的体现" |
| **学习成本** | 低，就是普通 Python 项目 | 中，需要理解工作空间概念 |
| **扩展性** | 加功能要改现有代码 | 加功能就是加新包 |

### 4.3 项目目录结构

```
agent-devtools-mcp/
│
├── pyproject.toml                    # 🌟 根工作空间（最重要的配置文件）
│                                      # 告诉 uv：下面 packages/ 里有 4 个小项目
│
├── packages/
│   ├── mcp-common/                   # 📦 公共基础库
│   │   ├── pyproject.toml
│   │   ├── src/mcp_common/
│   │   │   ├── __init__.py
│   │   │   ├── security/             # 🔒 安全模块
│   │   │   │   ├── __init__.py
│   │   │   │   ├── sandbox.py        #   安全沙箱（三层防御核心）
│   │   │   │   ├── path_validator.py #   路径校验（防穿越）
│   │   │   │   ├── command_validator.py # 命令校验（防注入）
│   │   │   │   └── sql_validator.py  #   SQL 校验（只读检查）
│   │   │   ├── logging/              # 📝 日志模块
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logger.py         #   结构化日志
│   │   │   │   └── trace.py          #   Trace ID 生成
│   │   │   ├── errors/               # ❌ 错误码模块
│   │   │   │   ├── __init__.py
│   │   │   │   ├── codes.py          #   错误码定义
│   │   │   │   └── handler.py        #   统一错误处理
│   │   │   ├── config/               # ⚙️ 配置管理
│   │   │   │   ├── __init__.py
│   │   │   │   ├── loader.py         #   配置加载器
│   │   │   │   └── schema.py         #   配置模型
│   │   │   ├── middleware/            # 🔗 拦截器链
│   │   │   │   ├── __init__.py
│   │   │   │   └── chain.py          #   拦截器链实现
│   │   │   └── models/               # 📐 公共数据模型
│   │   │       ├── __init__.py
│   │   │       └── base.py
│   │   │
│   │   ├── tests/
│   │   │   ├── test_sandbox.py
│   │   │   ├── test_path_validator.py
│   │   │   ├── test_command_validator.py
│   │   │   ├── test_sql_validator.py
│   │   │   └── test_trace.py
│   │   │
│   │   └── README.md
│   │
│   ├── mcp-devtools/                 # 🛠 开发工具服务
│   │   ├── pyproject.toml
│   │   ├── src/mcp_devtools/
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py           # python -m mcp_devtools 入口
│   │   │   ├── server.py             # MCP Server 入口（注册工具、启动服务）
│   │   │   ├── tools/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── file_ops.py       # read_file / write_file
│   │   │   │   ├── command.py        # run_command / run_async_command
│   │   │   │   └── git_ops.py        # git_status / git_diff
│   │   │   └── config.py             # 模块特有配置
│   │   │
│   │   ├── tests/
│   │   │   ├── test_file_ops.py
│   │   │   ├── test_command.py
│   │   │   └── test_git_ops.py
│   │   │
│   │   └── README.md
│   │
│   ├── mcp-dbtools/                  # 🗄 数据库访问服务
│   │   ├── pyproject.toml
│   │   ├── src/mcp_dbtools/
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── server.py
│   │   │   ├── adapters/             # 数据库适配器（策略模式）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py           # DatabaseAdapter 抽象基类
│   │   │   │   └── sqlite_adapter.py # SQLite 实现（先用这个）
│   │   │   ├── tools/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── metadata.py       # list_tables / describe_table
│   │   │   │   └── query.py          # execute_select / query_with_pagination
│   │   │   └── config.py
│   │   │
│   │   ├── tests/
│   │   │   ├── test_metadata.py
│   │   │   ├── test_query.py
│   │   │   └── test_sqlite_adapter.py
│   │   │
│   │   └── README.md
│   │
│   └── mcp-kbtools/                  # 📚 知识库服务
│       ├── pyproject.toml
│       ├── src/mcp_kbtools/
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   ├── server.py
│       │   ├── ingestion/            # 文档处理
│       │   │   ├── __init__.py
│       │   │   ├── loader.py         # 文档加载（支持 md/txt/pdf）
│       │   │   └── splitter.py       # 文本分块
│       │   ├── retrieval/            # 检索
│       │   │   ├── __init__.py
│       │   │   ├── bm25_engine.py    # 关键词搜索（Whoosh）
│       │   │   ├── vector_engine.py  # 向量搜索（可选）
│       │   │   └── hybrid.py         # 混合搜索（RRF 融合）
│       │   ├── tools/
│       │   │   ├── __init__.py
│       │   │   ├── kb_manage.py      # create_kb / list_kbs
│       │   │   ├── kb_docs.py        # add_document / delete_document
│       │   │   └── kb_search.py      # semantic_search
│       │   └── config.py
│       │
│       ├── tests/
│       │   ├── test_splitter.py
│       │   ├── test_bm25_engine.py
│       │   └── test_kb_search.py
│       │
│       └── README.md
│
├── tests/                            # 🌐 跨模块集成测试
│   ├── conftest.py
│   └── test_integration.py
│
├── docs/                             # 📖 文档
│   ├── architecture.md               # 架构设计图
│   ├── security.md                   # 安全设计详解
│   ├── devtools-module.md
│   ├── dbtools-module.md
│   ├── kbtools-module.md
│   └── deployment.md                 # 部署指南
│
├── scripts/                          # 🛠 辅助脚本
│   └── demo.py                       # 演示脚本
│
├── examples/                         # 📋 配置示例
│   └── claude_desktop_config.json    # Claude Desktop 配置
│
├── Dockerfile                        # 🐳 容器化部署
├── .github/
│   └── workflows/
│       ├── ci.yml                    # CI：测试 + 代码质量
│       └── release.yml              # 发布：PyPI + Docker
│
├── Makefile                          # 常用快捷命令
└── README.md                         # 项目总介绍
```

### 4.4 各模块职责一览

| 包 | 类型 | 职责 | 关键依赖 |
|:---|:-----|:-----|:---------|
| **mcp-common** | 库（被依赖） | 安全、日志、错误码、配置、拦截器 | mcp, pydantic |
| **mcp-devtools** | 应用（可执行） | 文件读写、命令执行、Git 查询 | mcp-common, typer |
| **mcp-dbtools** | 应用（可执行） | 数据库列表/表结构/查询 | mcp-common |
| **mcp-kbtools** | 应用（可执行） | 知识库管理、文档索引、语义搜索 | mcp-common, whoosh |

### 4.5 什么是工作空间？怎么配置？

> 🧐 **对初学者解释工作空间：**
> 
> 普通的 Python 项目只有一个 `pyproject.toml`，所有代码在一个目录里。
> 工作空间就是**一个总配置文件管着多个小项目**。
> 
> 比如你的项目有 4 个小项目（common / devtools / dbtools / kbtools），
> 如果不用工作空间，你要 cd 进每个目录分别 `pip install`。
> 用了工作空间，在根目录执行 `uv sync`，一次装完所有依赖。

**根 `pyproject.toml` 配置：**

```toml
[project]
name = "agent-devtools-mcp"
version = "0.1.0"
description = "生产级 MCP 工具网关套件"
requires-python = ">=3.12"

# 告诉 uv：packages/ 目录下有 4 个小项目
[tool.uv.workspace]
members = [
    "packages/mcp-common",
    "packages/mcp-devtools",
    "packages/mcp-dbtools",
    "packages/mcp-kbtools",
]
```

**每个子包的 `pyproject.toml`（以 mcp-common 为例）：**

```toml
[project]
name = "mcp-common"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]
```

**你的日常操作只有 3 个命令：**

```bash
# 1. 第一次下载项目后，装所有依赖
uv sync

# 2. 运行某个模块（比如 devtools）
uv run --package mcp-devtools python -m mcp_devtools

# 3. 运行所有测试
uv run pytest
```

---

## 5. 三大模块详解

### 5.1 模块总览

| 模块 | 工具数量 | 难度 | 建议开发顺序 | 关键安全特性 |
|:-----|:---------|:-----|:------------|:------------|
| **mcp-devtools** 🛠 | 6 个工具（4 个必做 + 2 个进阶） | ⭐⭐⭐ 最难 | **第 1 个开发** | 路径沙箱 + 命令白名单 |
| **mcp-dbtools** 🗄 | 3 个工具（全部必做） | ⭐⭐ 中等 | **第 2 个开发** | SQL 语法解析拦截 |
| **mcp-kbtools** 📚 | 3 个工具（全部必做） | ⭐⭐ 中等 | **第 3 个开发** | 文件类型校验 |

---

### 5.2 mcp-devtools 模块（开发工具）

#### 模块定位

让 AI Agent 能安全地读写文件、执行命令、查看 Git 状态。这是**安全要求最高**的模块，因为文件操作和命令执行直接接触操作系统。

#### 工具清单

| 工具名 | 读写 | 描述 | 优先级 |
|:-------|:-----|:-----|:-------|
| `read_file` | 只读 | 读取文件内容 | **必做** P0 |
| `write_file` | **读写** | 写入文件内容（默认禁用） | **必做** P0 |
| `run_command` | **读写** | 执行终端命令（默认禁用） | **必做** P0 |
| `git_status` | 只读 | 查看 Git 工作区状态 | **必做** P0 |
| `git_diff` | 只读 | 查看文件改动详情 | 进阶 P1 |
| `run_async_command` | **读写** | 异步执行长命令（默认禁用） | 进阶 P1 |

> **为什么 git_status 和 git_diff 是必做？** 面试演示时最常问的就是"能查 Git 仓库状态吗"，这两个工具演示效果最好。

#### 工具详细定义

<details>
<summary><b>① read_file — 读取文件（必做）</b></summary>

```
工具名: read_file
描述: 读取工作目录内的文本文件内容
权限: 只读
安全级别: SAFE

输入参数:
  file_path (string, 必填): 相对于工作目录的文件路径
  encoding (string, 可选, 默认"utf-8"): 文件编码

输出:
  返回文件内容（字符串），最大 1MB

安全约束（必须实现的三道检查）:
  1. 路径校验: 使用 pathlib.Path.resolve() 规范化路径
     → 拒绝包含 ".." 的路径（路径遍历攻击防护）
     → 拒绝访问工作目录外的文件
  2. 文件类型校验: 只允许读取文本文件（.md/.py/.txt/.json/.yaml/.toml/.js/.ts/.html/.css）
     → 拒绝读取 .exe/.dll/.so/.bin 等二进制文件
  3. 大小限制: 超过 1MB 的文件拒绝读取（防止撑爆内存）

示例:
  输入: {"file_path": "src/server.py"}
  输出: "from mcp.server.fastmcp import FastMCP\n..."

错误场景:
  - 文件不存在 → "文件不存在: src/server.py，请检查路径"
  - 路径越权 → "路径越权: 只允许操作工作目录内的文件"
  - 文件太大 → "文件超过 1MB 限制，暂不支持大文件"
```

</details>

<details>
<summary><b>② write_file — 写入文件（必做·默认禁用）</b></summary>

```
工具名: write_file
描述: 向文件写入内容（覆盖写入）
权限: 读写（默认禁用，需在配置中显式启用）
安全级别: DANGEROUS

输入参数:
  file_path (string, 必填): 相对于工作目录的文件路径
  content (string, 必填): 要写入的内容
  create_parent (boolean, 可选, 默认false): 是否自动创建父目录

安全约束:
  1. 路径校验: 同 read_file，必须经过路径穿越防护
  2. 配置开关: 必须配置 devtools.allow_write=true 才能使用
  3. 原子写入: 使用「临时文件 + 重命名」机制，防止写入中断导致文件损坏
     → 先写入 .tmp 文件，再重命名为目标文件
  4. 内容扫描: 检查写入内容是否包含危险代码（可选，进阶特性）
  5. 审计日志: 每次写入记录（谁/什么时间/写的什么文件/文件大小）

输出:
  "文件写入成功: src/server.py (2.3KB)"

示例:
  输入: {"file_path": "README.md", "content": "# My Project\n..."}
  输出: "文件写入成功: README.md (128B)"

错误场景:
  - 写入未启用 → "写入操作未启用，请在配置中设置 devtools.allow_write=true"
  - 路径越权 → "路径越权: 只允许操作工作目录内的文件"
  - 父目录不存在 → "父目录不存在，设置 create_parent=true 自动创建"
```

**面试亮点：原子写入**

```python
# 不是这么写（直接覆盖，如果写入中途崩溃，原文件损坏）：
# with open(path, "w") as f:
#     f.write(content)

# 而是这么写（写临时文件 → 重命名，保证安全性）：
import os, tempfile

def atomic_write(path: Path, content: str) -> None:
    """原子写入：先写临时文件，再重命名"""
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.tmp.",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(fd)  # 强制写入磁盘
        os.replace(tmp_path, path)  # 原子替换
    except Exception:
        os.unlink(tmp_path)  # 失败则删除临时文件
        raise
```

> **对面试官说：** *"我的文件写入用了原子写入机制，不是直接 open() write()。这样即使写入中途服务器崩溃，也不会产生半截文件，保证了数据完整性。"*

</details>

<details>
<summary><b>③ run_command — 执行命令（必做·默认禁用）</b></summary>

```
工具名: run_command
描述: 在工作目录内执行白名单中的终端命令
权限: 读写（默认禁用，需在配置中显式启用）
安全级别: DANGEROUS

输入参数:
  command (string, 必填): 命令名（如 "git", "python", "ls"）
  args (array of string, 可选): 命令参数列表（如 ["status"]）
  timeout (integer, 可选, 默认30): 超时时间（秒）

安全约束（核心，必须实现）:
  1. 命令白名单: 只允许预设的命令（默认: git, python, uv, pip, ls, cat, grep, find, pwd, echo）
     非白名单命令直接拦截
  2. 禁止 shell 模式: 使用 subprocess.run([command, ...args], shell=False)
     禁止使用 shell=True（这是命令注入的根源）
     从根源上杜绝 "git; rm -rf /" 这种注入攻击
  3. 参数校验: 拒绝包含危险字符的参数: ; ` $ | && ||
  4. 超时控制: 超过 timeout 秒自动 kill 进程（默认 30s）
  5. 输出限制: stdout 最多返回 5000 行 / 1MB
  6. 交互命令禁止: 自动关闭 stdin，禁止需要人工输入的命令

安全原理（为什么要禁用 shell=True）:
  ┌─────────────────────────────────────────────────────────┐
  │ shell=True: 命令被传给 /bin/sh 解释执行                │
  │   run("git status; rm -rf /", shell=True)  ← 危险！    │
  │   分号后的 rm -rf / 也会被执行                           │
  │                                                         │
  │ shell=False: 命令以数组形式直接执行                     │
  │   run(["git", "status"])  ← 安全                        │
  │   run(["git", "status; rm -rf /"])  ← 被当作文件名     │
  │   分号不会被解释为命令分隔符                             │
  └─────────────────────────────────────────────────────────┘

输出:
  返回命令的 stdout 和 stderr 内容

示例:
  输入: {"command": "git", "args": ["status"]}
  输出: "On branch main\nYour branch is up to date with 'origin/main'.\n\nnothing to commit, working tree clean"

错误场景:
  - 命令不在白名单 → "命令 'rm' 不在白名单内，允许的命令: git, python, uv, ..."
  - 参数包含危险字符 → "参数包含危险字符: $，已拦截"
  - 执行超时 → "命令执行超时（30s），已强制终止"
  - 命令不存在 → "命令 'xyz' 未找到，请检查是否已安装"
```

> ⚠️ **你一定要理解的：为什么 shell=False 如此重要**
>
> 假设某天你收到一个来自 AI Agent 的请求：`git status; rm -rf /`
> - 如果用了 `shell=True`，bash 会先执行 git status，然后执行 `rm -rf /`（删库跑路）
> - 如果用了 `shell=False`，系统会找一个叫 `git status; rm -rf /` 的程序，找不到就报错
>
> 这就是**命令注入**——AI Agent 可能被诱导发送恶意命令。用 `shell=False` 从根源上杜绝。

</details>

<details>
<summary><b>④ git_status — 查看 Git 状态（必做）</b></summary>

```
工具名: git_status
描述: 查看 Git 仓库的工作区状态
权限: 只读（开箱即用）
安全级别: SAFE

实现方式:
  本质是调用 run_command 的安全子集，但作为独立工具暴露
  
  内部实现: subprocess.run(["git", "status", "--short"], ...)

输入参数: 无（自动使用工作目录）

输出:
  返回 git status --short 格式的输出

示例:
  输入: {}
  输出: " M src/server.py\n?? new_file.py"

错误场景:
  - 不是 Git 仓库 → "当前目录不是 Git 仓库"
  - Git 未安装 → "Git 未安装，请先安装 Git"
```

</details>

<details>
<summary><b>⑤ git_diff — 查看文件改动（进阶）</b></summary>

```
工具名: git_diff
描述: 查看未暂存的文件改动详情
权限: 只读
安全级别: SAFE

输入参数:
  path (string, 可选): 限定查看某个文件的改动

输出:
  返回 diff 格式文本，最大 100KB

实现方式:
  subprocess.run(["git", "diff", path], ...)

安全约束:
  - path 必须经过路径穿越防护
  - 输出大小限制 100KB

示例:
  输入: {"path": "src/server.py"}
  输出: "diff --git a/src/server.py b/src/server.py\n..."
```

</details>

<details>
<summary><b>⑥ run_async_command — 异步执行命令（进阶·默认禁用）</b></summary>

```
工具名: run_async_command
描述: 异步执行耗时命令，立即返回任务 ID（适用于构建、安装等长任务）
权限: 读写（默认禁用）
安全级别: DANGEROUS

输入参数:
  command (string, 必填): 命令名
  args (array of string, 可选): 参数列表
  timeout (integer, 可选, 默认300): 超时时间（5分钟）

输出:
  返回任务 ID，客户端可用此 ID 查询进度

示例:
  输入: {"command": "pip", "args": ["install", "numpy"]}
  输出: "任务已启动，任务 ID: task_abc123"
```

</details>

#### mcp-devtools 安全流程图

```
工具调用请求
     │
     ▼
┌─────────────────────┐
│  第1步: 配置检查     │ ← 写入工具是否已启用？
│  (只读工具直接放行)  │     否 → 返回"未启用，请配置"
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  第2步: 路径校验     │ ← 包含 .. ？ 在工作目录外？
│  (文件类工具)        │     是 → 拒绝
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  第3步: 命令校验     │ ← 命令在白名单？参数含危险字符？
│  (命令类工具)        │     否 → 拒绝
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  第4步: 执行 + 限制   │ ← 超时控制 + 输出大小限制
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  第5步: 审计日志     │ ← 记录谁/何时/调用了什么/结果
└─────────┬───────────┘
          ▼
       返回结果 ✅
```

---

### 5.3 mcp-dbtools 模块（数据库访问）

#### 模块定位

让 AI Agent 能安全地查询数据库。核心原则是**只读、受控、可审计**。

#### 技术实现：策略模式

```python
# 核心设计：数据库适配器抽象
# 好处：以后加 PostgreSQL、MySQL 只需要写一个新的适配器类

from abc import ABC, abstractmethod

class DatabaseAdapter(ABC):
    """数据库适配器 - 所有数据库类型的统一接口"""

    @abstractmethod
    async def list_tables(self) -> list[str]:
        ...

    @abstractmethod
    async def describe_table(self, table: str) -> list[dict]:
        ...

    @abstractmethod
    async def execute_select(self, sql: str, params: dict | None = None,
                              limit: int = 100) -> list[dict]:
        ...

    @abstractmethod
    async def close(self):
        ...


class SQLiteAdapter(DatabaseAdapter):
    """SQLite 实现（项目第一期只做这个）"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None

    async def list_tables(self) -> list[str]:
        # SELECT name FROM sqlite_master WHERE type='table'
        ...

# 以后加 PostgreSQL 只需要：
# class PostgreSQLAdapter(DatabaseAdapter):
#     ...
```

#### 工具清单

| 工具名 | 描述 | 优先级 |
|:-------|:-----|:-------|
| `list_tables` | 列出数据库所有表 | **必做** P0 |
| `describe_table` | 查看表结构（字段名/类型/约束） | **必做** P0 |
| `execute_select` | 执行 SELECT 查询 | **必做** P0 |

#### 工具详细定义

<details>
<summary><b>① list_tables — 列出数据库表（必做）</b></summary>

```
工具名: list_tables
描述: 列出数据库中的所有表
权限: 只读
安全级别: SAFE

输入参数: 无

输出:
  返回表名列表

示例:
  输入: {}
  输出: "users\norders\nproducts\nreviews"

错误场景:
  - 数据库连接失败 → "数据库连接失败，请检查配置中的数据库路径"
  - 数据库文件不存在 → "数据库文件不存在"
```

</details>

<details>
<summary><b>② describe_table — 查看表结构（必做）</b></summary>

```
工具名: describe_table
描述: 查看指定表的字段、类型、约束
权限: 只读
安全级别: SAFE

输入参数:
  table_name (string, 必填): 表名

输出:
  返回表结构信息（字段名/类型/是否可为空/主键/默认值）

示例:
  输入: {"table_name": "users"}
  输出:
    "id         INTEGER  NOT NULL  PRIMARY KEY
     name       TEXT     NOT NULL
     email      TEXT     NOT NULL  UNIQUE
     created_at TEXT    NOT NULL  DEFAULT CURRENT_TIMESTAMP"

安全约束:
  - table_name 必须是合法的 SQL 标识符（只含字母、数字、下划线）
  - 使用参数化查询，禁止拼接表名
```

</details>

<details>
<summary><b>③ execute_select — 执行 SELECT 查询（必做）</b></summary>

```
工具名: execute_select
描述: 执行 SQL SELECT 查询
权限: 只读
安全级别: SAFE_WITH_CHECK

输入参数:
  query (string, 必填): SELECT 查询语句
  params (dict, 可选): 查询参数（参数化查询）
  limit (integer, 可选, 默认100, 最大1000): 返回行数上限

安全约束（核心）:
  1. SQL 白名单: 只允许 SELECT 开头的查询
     → 用 SQL 解析器（sqlglot 或正则）检查
     → 拦截 INSERT/UPDATE/DELETE/DROP/ALTER 等
  2. 单语句检查: 禁止多条 SQL 一起执行（防止 "; DROP TABLE" 注入）
  3. 参数化查询: 用户传入的值通过 ? 占位符传入
     → 错误示范: f"SELECT * FROM users WHERE id = {user_input}"  ← 危险！
     → 正确示范: "SELECT * FROM users WHERE id = ?" 传参
  4. 自动 LIMIT: 无论用户写不写 LIMIT，都限制最大 1000 行
  5. 超时控制: 查询超过 30 秒自动终止

输出:
  返回 JSON 格式的查询结果

示例:
  输入: {"query": "SELECT id, name, email FROM users WHERE created_at > ?",
         "params": {"created_at": "2026-06-01"}}
  输出: '[{"id": 1, "name": "张三", "email": "zhangsan@example.com"}]'

错误场景:
  - 非 SELECT 查询 → "仅允许 SELECT 查询，检测到 DELETE 语句"
  - 多条语句 → "不允许执行多条语句"
  - 查询超时 → "查询执行超时（30s），建议优化 SQL 或增加索引"
```

> ⚠️ **你一定要理解：什么 SQL 是危险的**
>
> ```
> ✅ 安全的: SELECT * FROM users WHERE id = ?
> ✅ 安全的: SELECT name, email FROM orders WHERE amount > 100
> ❌ 危险的: DROP TABLE users（删表）
> ❌ 危险的: users; DROP TABLE users; --（分号注入）
> ❌ 危险的: ' OR '1'='1（恒真注入，绕过登录）
> ```

</details>

#### SQL 防护核心代码

```python
# packages/mcp-common/src/mcp_common/security/sql_validator.py
import re

# 写入操作关键字
WRITE_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|"
    r"GRANT|REVOKE|EXEC|EXECUTE|CALL|MERGE)\s",
    re.IGNORECASE,
)


def validate_readonly_query(sql: str) -> None:
    """验证 SQL 查询是只读的"""
    stripped = sql.strip()

    # 1. 必须以只读关键字开头
    if not re.match(r"^(SELECT|EXPLAIN|DESCRIBE|SHOW|WITH)\s", stripped, re.IGNORECASE):
        raise SecurityError("仅允许只读查询（SELECT/EXPLAIN/DESCRIBE/SHOW）")

    # 2. 不能包含写入关键字
    if WRITE_PATTERNS.search(stripped):
        raise SecurityError("查询中包含被禁止的写入操作")

    # 3. 不能有多条语句（防止分号注入）
    # 先移除字符串里的分号（字符串中的分号安全）
    cleaned = re.sub(r"'.*?'", "", stripped)
    if ";" in cleaned.rstrip(";"):
        raise SecurityError("不允许执行多条语句")


def validate_table_name(name: str) -> None:
    """验证表名合法性"""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise SecurityError(f"非法的表名: {name}")
```

---

### 5.4 mcp-kbtools 模块（知识库）

#### 模块定位

让 AI Agent 能搜索项目文档。AI Agent 要编程时需要参考文档，kb 模块提供这个能力。

#### 为什么先做关键词搜索（BM25）而不是向量搜索？

| 搜索方式 | 原理 | 优点 | 缺点 | 依赖 |
|:---------|:-----|:-----|:-----|:-----|
| **BM25 关键词** | 统计关键词出现频率 | 精确匹配好，速度快 | 不理解语义 | 不需要 AI 模型 |
| **向量搜索** | 将文本转为向量，算相似度 | 理解语义 | 需要模型，速度慢 | sentence-transformers |

> **我们的策略：** 第一期只做 BM25。因为：
> 1. 零外部依赖（不需要下载 AI 模型）
> 2. 搜索代码库时，关键词匹配其实比语义搜索更准（函数名、变量名就是关键词）
> 3. 后期可以作为进阶功能加上向量搜索

#### 工具清单

| 工具名 | 描述 | 优先级 |
|:-------|:-----|:-------|
| `create_kb` | 创建知识库 | **必做** P0 |
| `add_document` | 添加文档到知识库 | **必做** P0 |
| `semantic_search` | 搜索知识库（关键词模式） | **必做** P0 |

#### 知识库存储设计

```
SQLite 数据库中存储:
┌─────────────────────────────────────────────────────────┐
│  kb_documents 表          kb_chunks 表                   │
│  ┌──────────────┐        ┌──────────────────────┐      │
│  │ id (主键)     │◄───┐  │ id (主键)             │      │
│  │ name          │    └──│ doc_id (外键)          │      │
│  │ description   │       │ chunk_index (块序号)   │      │
│  └──────────────┘       │ content (文本内容)     │      │
│                          │ start_line (起始行)    │      │
│  kb_fts (虚拟表)         │ end_line (结束行)      │      │
│  ┌──────────────┐       └──────────────────────┘      │
│  │ 全文索引      │                                      │
│  │ (FTS5引擎)    │      用 Whoosh 做 BM25 索引            │
│  └──────────────┘       Whoosh 把数据存到文件系统         │
└─────────────────────────────────────────────────────────┘
```

#### 工具详细定义

<details>
<summary><b>① create_kb — 创建知识库（必做）</b></summary>

```
工具名: create_kb
描述: 创建一个新的知识库
权限: 读写
安全级别: SAFE

输入参数:
  name (string, 必填): 知识库名称（字母数字下划线）
  description (string, 可选): 知识库描述

输出:
  返回创建结果

示例:
  输入: {"name": "my_project_docs", "description": "项目文档"}
  输出: "知识库创建成功: my_project_docs"
```

</details>

<details>
<summary><b>② add_document — 添加文档（必做）</b></summary>

```
工具名: add_document
描述: 向知识库中添加一个文档文件
权限: 读写
安全级别: SAFE_WITH_CHECK

输入参数:
  kb_name (string, 必填): 知识库名称
  file_path (string, 必填): 文档文件路径（相对于工作目录）
  chunk_size (integer, 可选, 默认500): 分块大小（字符数）

支持的文档格式:
  - .md (Markdown)
  - .txt (纯文本)
  - .py / .js / .ts / .java (代码文件)
  - .json / .yaml / .toml (配置文件)

处理流程:
  1. 读取文件内容
  2. 按段落分块（chunk_size 控制每块大小）
  3. 用 Whoosh 建立 BM25 索引
  4. 存储文档元数据到 SQLite

输出:
  返回索引结果统计

示例:
  输入: {"kb_name": "my_project_docs", "file_path": "README.md"}
  输出: "文档添加成功: README.md (共 8 个分块)"

错误场景:
  - 知识库不存在 → "知识库 'xxx' 不存在，请先调用 create_kb"
  - 文件不存在 → "文件不存在: xxx"
  - 不支持的文件格式 → "不支持的文件格式: .exe，支持的格式: .md, .txt, .py, ..."
```

</details>

<details>
<summary><b>③ semantic_search — 搜索知识库（必做）</b></summary>

```
工具名: semantic_search
描述: 在知识库中搜索与查询最相关的文档内容
权限: 只读
安全级别: SAFE

输入参数:
  kb_name (string, 必填): 知识库名称
  query (string, 必填): 搜索关键词
  top_k (integer, 可选, 默认5, 最大20): 返回结果数量

搜索原理:
  使用 BM25 算法（关键词频率 + 文档长度归一化）
  - 查询分词 → 在 Whoosh 索引中搜索 → 按 BM25 分数排序 → 返回 Top-K

输出:
  返回相关文档块列表（文件名/行号/相关度分数/内容摘要）

示例:
  输入: {"kb_name": "my_project_docs", "query": "数据库连接配置", "top_k": 3}
  输出:
    "1. docs/setup.md:45-50  (分数: 0.92)
        配置数据库连接：DATABASE_URL = "sqlite:///local.db"

     2. .env.example:1-3  (分数: 0.71)
        DATABASE_URL=..."

错误场景:
  - 知识库不存在 → "知识库 'xxx' 不存在"
  - 知识库为空 → "知识库为空，请先调用 add_document 添加文档"
```

</details>

---

## 6. 三层纵深安全防御体系

> 🎯 **这是项目最大的面试亮点。** 大多数求职者的项目没有安全设计，而你的项目有体系化的三层防御。

### 6.1 三层防御总览

```
┌────────────────────────────────────────────────────────────┐
│                    第一层：边界防护                          │
│  "不让坏人进门"                                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐   │
│  │ 工作区隔离            │  │ 命令白名单                │   │
│  │ 所有文件操作限制在     │  │ 只允许预设的命令被执行    │   │
│  │ 指定工作目录内         │  │ 非白名单命令直接拒绝      │   │
│  └──────────────────────┘  └──────────────────────────┘   │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼──────────────────────────────┐
│                    第二层：操作管控                          │
│  "就算进来了也搞不了破坏"                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │路径穿越   │ │命令注入   │ │ SQL 只读  │ │输出大小   │     │
│  │防护       │ │防护       │ │校验      │ │限制      │     │
│  │拒绝 ..    │ │拒绝 ; ` $ │ │拦截非    │ │超大输出   │     │
│  │路径      │ │等特殊字符 │ │SELECT   │ │自动截断  │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼──────────────────────────────┐
│                    第三层：审计追溯                          │
│  "干了啥都有记录"                                           │
│  ┌──────────────────────┐  ┌──────────────────────────┐   │
│  │ 审计日志              │  │ Trace ID 透传            │   │
│  │ 每次工具调用都记录     │  │ 每个请求一个唯一 ID      │   │
│  │ 谁/何时/调用了什么/    │  │ 贯穿整个调用链路         │   │
│  │ 结果如何               │  │ 方便问题排查             │   │
│  └──────────────────────┘  └──────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### 6.2 第一层：边界防护

**做什么：** 在入口处拦截非法请求，不让危险操作进入系统。

#### ① 工作区隔离

```python
# packages/mcp-common/src/mcp_common/security/path_validator.py

from pathlib import Path


class PathValidator:
    """路径校验器：防止路径遍历攻击"""

    def __init__(self, workspace_root: str | Path):
        # workspace_root 是允许操作的工作目录（如 /home/user/projects）
        self.workspace_root = Path(workspace_root).resolve()

    def validate(self, target_path: str) -> Path:
        """校验并返回安全的绝对路径"""
        # 1. 拼接并规范化（解析 .. 和软链接）
        resolved = (self.workspace_root / target_path).resolve()

        # 2. 检查是否在工作目录内
        if not str(resolved).startswith(str(self.workspace_root)):
            raise PermissionError(
                f"路径越权: {target_path}，只允许操作工作目录内的文件"
            )

        return resolved
```

> **工作原理：** 用户传 `../../etc/passwd` → 拼接后变成 `/home/user/projects/../../etc/passwd`
> → `resolve()` 解析为 `/etc/passwd` → 不在工作目录内 → 拒绝 ✅

#### ② 命令白名单

```python
# packages/mcp-common/src/mcp_common/security/command_validator.py

class CommandValidator:
    """命令校验器：防止命令注入"""

    # 默认白名单
    DEFAULT_ALLOWED_COMMANDS = {
        "git", "python", "uv", "pip",
        "ls", "cat", "grep", "find", "pwd", "echo",
        "node", "npm", "npx",
    }

    def __init__(self, allowed_commands: set[str] | None = None):
        self.allowed = allowed_commands or self.DEFAULT_ALLOWED_COMMANDS

    def validate(self, command: str, args: list[str]) -> None:
        """校验命令和参数"""
        # 1. 命令必须在白名单中
        if command not in self.allowed:
            raise PermissionError(
                f"命令 '{command}' 不在白名单内。"
                f"允许的命令: {', '.join(sorted(self.allowed))}"
            )

        # 2. 参数不能包含危险字符
        dangerous = {";", "`", "$", "|", "&&", "||", ">", "<", "&"}
        for arg in args:
            for char in dangerous:
                if char in arg:
                    raise PermissionError(
                        f"参数包含危险字符 '{char}'，已拦截"
                    )
```

### 6.3 第二层：操作管控

**做什么：** 就算请求通过了边界防护，在执行时还要二次检查。

| 检查项 | 检查什么 | 对应工具 |
|:-------|:---------|:---------|
| 路径穿越防护 | 文件路径是否包含 `..` | read_file, write_file |
| 命令注入防护 | 参数是否包含 `;` `` ` `` `$` | run_command |
| SQL 只读校验 | 是否只执行 SELECT | execute_select |
| 输出大小限制 | 返回结果是否超过 1MB | 所有工具 |
| 执行超时控制 | 命令/查询是否超时 | run_command, execute_select |

### 6.4 第三层：审计追溯

**做什么：** 所有操作都有记录，出了问题能查。

#### 审计日志格式

```python
# packages/mcp-common/src/mcp_common/logging/logger.py

import structlog  # 结构化日志库
import uuid

# 每次工具调用记录以下信息
audit_entry = {
    "timestamp": "2026-06-15T10:30:00+08:00",  # 什么时候发生的
    "trace_id": "trace_abc123",                  # 这次调用的唯一 ID
    "tool": "write_file",                        # 调用了什么工具
    "args_safe": {"file_path": "README.md"},     # 参数（脱敏，不记录文件内容）
    "caller": "mcp-client",                      # 谁调用的
    "status": "success",                         # 结果状态
    "duration_ms": 125,                          # 耗时
    "error": None,                               # 错误信息（如果有）
}

# 每次危险操作（写入类工具）强制写审计日志，不可关闭
```

#### Trace ID 透传

```python
import uuid
from contextvars import ContextVar

# ContextVar 是 Python 3.7+ 的特性
# 它让同一个请求的不同函数之间共享同一个变量
# 而不同请求之间不会互相干扰
current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """生成唯一的 Trace ID"""
    return f"trace_{uuid.uuid4().hex[:12]}"


def get_trace_id() -> str:
    return current_trace_id.get()


def set_trace_id(trace_id: str) -> None:
    current_trace_id.set(trace_id)
```

---

## 7. 统一工程化规范

### 7.1 代码风格

| 规范 | 标准 |
|:-----|:-----|
| **格式化** | Ruff（与 1 号项目一致） |
| **类型注解** | 所有函数必须标注参数和返回值类型 |
| **行长度** | 100 字符 |
| **Docstring** | Google 风格 |
| **命名** | 文件: `snake_case` / 类: `PascalCase` / 函数: `snake_case` / 常量: `UPPER_SNAKE` |

```python
# Google 风格 Docstring 示例
def validate_readonly_query(sql: str) -> bool:
    """检查 SQL 查询是否为只读。

    Args:
        sql: 要检查的 SQL 查询字符串。

    Returns:
        如果是只读查询返回 True，否则返回 False。

    Raises:
        SecurityError: 如果包含写入操作或危险模式。

    Examples:
        >>> validate_readonly_query("SELECT * FROM users")
        True
        >>> validate_readonly_query("DROP TABLE users")
        False
    """
    ...
```

### 7.2 统一错误处理

所有工具必须返回统一的错误格式：

```
✅ 正确格式：
   ❌ 查询被拒绝：仅允许只读查询（SELECT/EXPLAIN/DESCRIBE/SHOW）
   💡 提示：如果确实需要写入操作，请配置 database.read_only=false
   🔗 参考：docs/security.md

❌ 错误格式（不要这样）：
   ❌ Error 10042
   ❌ 数据库错误
   ❌ 出错了，请重试
```

**错误三要素：**
1. ✅ **发生了什么**（用户能理解的语言）
2. 💡 **怎么解决**（给出具体操作建议）
3. 🔗 **参考文档**（指向配置文档或工具文档）

### 7.3 统一配置管理

支持两种配置方式，优先级：**环境变量 > 配置文件 > 默认值**

```yaml
# 配置文件示例（config.yaml）
devtools:
  workspace_root: /home/user/projects
  allow_write: false
  allowed_commands:
    - git
    - python
    - uv
  command_timeout: 30

database:
  db_path: ./local.db
  read_only: true
  max_rows: 1000
  query_timeout: 30

knowledge_base:
  data_dir: ./kb_data
  default_top_k: 5
```

```bash
# 同样可以用环境变量配置
export DEVTOOLS_ALLOW_WRITE=true
export DB_PATH=/data/mydb.sqlite
```

### 7.4 拦截器机制（通用能力）

拦截器是**统一处理横切关注点**的模式。比如每个工具都要记录日志、检查权限，如果在每个工具里都写一遍就重复了。

```python
# 拦截器链 —— 所有工具调用前自动执行

class Interceptor:
    """拦截器基类"""
    async def before(self, tool_name: str, args: dict) -> None:
        """工具调用前执行"""
        ...

    async def after(self, tool_name: str, args: dict, result: any) -> None:
        """工具调用后执行"""
        ...


class LoggingInterceptor(Interceptor):
    """日志拦截器——记录每次调用"""

    async def before(self, tool_name: str, args: dict) -> None:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
        logger.info("tool_call_start", tool=tool_name, trace_id=trace_id)

    async def after(self, tool_name: str, args: dict, result: any) -> None:
        logger.info("tool_call_end", tool=tool_name, duration=...)
```

### 7.5 生产级可靠性设计

| 特性 | 说明 | 在哪个模块实现 |
|:-----|:-----|:-------------|
| **三级超时** | 协议层(60s) > 工具层(30s) > 命令层(30s) | mcp-common |
| **并发限流** | 单客户端最多 10 个并发调用 | mcp-common 拦截器 |
| **优雅启停** | 收到停止信号 → 拒绝新请求 → 等任务完成 → 退出 | 各模块 server.py |
| **原子写入** | 先写临时文件，再重命名 | mcp-devtools |

### 7.6 质量门禁（CI 检查项）

| 检查项 | 通过标准 |
|:-------|:---------|
| Ruff lint | 零 warning |
| mypy 类型检查 | 零 error |
| pytest 测试 | 100% 通过 |
| 覆盖率 | ≥90% |
| 安全测试 | 零失败 |

---

## 8. 测试规范

### 8.1 测试金字塔

```
        ┌──────┐
        │ E2E  │  ← 集成测试（1-2 个，验证整体流程）
       ┌┴──────┴┐
      ┌┴────────┴┐
     ┌┴──────────┴┐  ← 安全测试（覆盖率 100%）
    ┌┴────────────┴┐
   ┌┴──────────────┴┐ ← 单元测试（覆盖率 ≥90%）
  ┌┴────────────────┴┐
 ┌────────────────────┐
 └────────────────────┘
```

### 8.2 测试文件清单

```
tests/（每个模块自己的 tests/ 目录）
├── mcp-common/
│   ├── test_path_validator.py
│   │   ├── test_validate_allowed_path
│   │   ├── test_validate_path_traversal    # 测试 .. 路径被拒绝
│   │   └── test_validate_outside_workspace # 测试工作目录外路径被拒
│   │
│   ├── test_command_validator.py
│   │   ├── test_allowed_command
│   │   ├── test_disallowed_command
│   │   ├── test_dangerous_chars
│   │   └── test_shell_injection_attempts   # 模拟各种注入攻击
│   │
│   ├── test_sql_validator.py
│   │   ├── test_select_allowed
│   │   ├── test_insert_rejected
│   │   ├── test_drop_rejected
│   │   ├── test_multi_statement_rejected   # 分号注入防护
│   │   └── test_injection_attempts         # 常见 SQL 注入模式
│   │
│   └── test_trace.py
│       └── test_trace_id_generation
│
├── mcp-devtools/
│   ├── test_file_ops.py
│   │   ├── test_read_file_success
│   │   ├── test_read_file_not_found
│   │   ├── test_read_file_outside_workspace
│   │   ├── test_write_file_success
│   │   └── test_write_file_disabled_by_default
│   │
│   ├── test_command.py
│   │   ├── test_run_command_success
│   │   ├── test_run_command_not_allowed
│   │   └── test_run_command_timeout
│   │
│   └── test_git_ops.py
│       ├── test_git_status_in_repo
│       └── test_git_status_not_repo
│
└── tests/（根目录的集成测试）
    └── test_integration.py
        ├── test_devtools_read_file_flow
        ├── test_dbtools_query_flow
        └── test_kbtools_search_flow
```

### 8.3 测试用例规范

每个测试函数必须包含 **Given / When / Then** 三段式注释：

```python
async def test_write_file_disabled_by_default():
    """写入工具默认应该被禁用"""
    # Given: 一个使用默认配置的工具
    tools = DevToolsServer()

    # When: 尝试写入文件
    result = await tools.call_tool("write_file", {
        "file_path": "test.txt",
        "content": "hello",
    })

    # Then: 应该返回禁用错误，而不是写入成功
    assert result.is_error is True
    assert "未启用" in result.error_message


# 安全测试：覆盖常见攻击模式
@pytest.mark.security
@pytest.mark.parametrize("attack_input", [
    "'; DROP TABLE users; --",        # SQL 注入
    "' OR '1'='1",                     # 恒真攻击
    "../../etc/passwd",                # 路径穿越
    "`cat /etc/passwd`",               # 命令注入
    "$(cat /etc/passwd)",              # 命令注入（变量）
    "& ping 8.8.8.8 &",               # 后台命令
])
async def test_security_attack_patterns(attack_input):
    """所有常见攻击模式应该被拦截"""
    ...
```

### 8.4 覆盖率目标

| 模块 | 行覆盖率 | 说明 |
|:-----|:--------|:-----|
| mcp-common/security | **100%** | 安全代码必须全覆盖 |
| mcp-common (其他) | ≥90% | |
| mcp-devtools | ≥90% | |
| mcp-dbtools | ≥90% | |
| mcp-kbtools | ≥85% | |

---

## 9. 部署与运行方案

### 9.1 本地开发模式（主力演示）

这是你面试演示的主要方式——本地启动，通过 stdio 与 Claude Desktop 通信。

```bash
# 1. 克隆项目
git clone https://github.com/你的名字/agent-devtools-mcp.git
cd agent-devtools-mcp

# 2. 安装依赖（一次）
uv sync

# 3. 运行某个模块（比如 devtools）
uv run --package mcp-devtools python -m mcp_devtools

# 4. 或者运行所有测试
uv run pytest
```

### 9.2 Claude Desktop 配置

```json
{
  "mcpServers": {
    "devtools": {
      "command": "uv",
      "args": [
        "run", "--package", "mcp-devtools",
        "python", "-m", "mcp_devtools",
        "--workspace", "D:/projects/my-project"
      ]
    },
    "dbtools": {
      "command": "uv",
      "args": [
        "run", "--package", "mcp-dbtools",
        "python", "-m", "mcp_dbtools",
        "--db-path", "./local.db"
      ]
    }
  }
}
```

### 9.3 Docker 部署

```dockerfile
FROM python:3.12-slim

# 安装 Git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装项目
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --no-dev

# 默认工作目录
VOLUME ["/workspace"]
WORKDIR /workspace

# 启动 devtools 服务
ENTRYPOINT ["uv", "run", "--package", "mcp-devtools", "python", "-m", "mcp_devtools"]
```

### 9.4 CI/CD 管道

```yaml
# .github/workflows/ci.yml — 持续集成
name: CI

on:
  push: { branches: [main] }
  pull_request: { branches: [main] }

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python-version }}" }

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Lint
        run: uv run ruff check packages/

      - name: Type check
        run: uv run mypy packages/

      - name: Test
        run: uv run pytest --cov=packages/ --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

---

## 10. 开发路线图（三阶段）

### 总体建议

- **第一优先级**：先把 `mcp-common` 写好（这是所有模块的基础）
- **第二优先级**：按 devtools → dbtools → kbtools 的顺序写
- **最重要的事**：**先让一个工具能跑起来！** 别追求完美，先跑通 `read_file`，然后再加安全校验

### 阶段一：基础求职版（预计 2-4 周）

> 目标：跑通核心流程，能演示，有基本安全防护

| 周次 | 做什么 | 产出 |
|:-----|:-------|:-----|
| **第 1 周** | **mcp-common 基础框架** | • 安全模块：路径校验、命令校验、SQL 校验<br>• 日志模块：结构化日志 + Trace ID<br>• 错误码模块：统一错误处理<br>• 配置加载器 |
| **第 2-3 周** | **mcp-devtools 核心工具** | • `read_file`（带路径沙箱 + 文件类型校验）<br>• `write_file`（原子写入 + 默认禁用）<br>• `run_command`（命令白名单 + shell=False）<br>• `git_status` |
| **第 3-4 周** | **mcp-dbtools + mcp-kbtools** | • `list_tables` / `describe_table` / `execute_select`<br>• `create_kb` / `add_document` / `semantic_search` |
| **穿插进行** | **测试** | 每个工具写完立刻写测试，覆盖正常路径 + 安全路径 |

**阶段一验收标准：**
- [ ] 4 个包的基本结构搭建完成，uv sync 可运行
- [ ] 安全模块三个校验器（路径/命令/SQL）通过测试
- [ ] devtools 至少 `read_file` + `git_status` 可调用
- [ ] dbtools 的 `list_tables` + `execute_select` 可查询本地 SQLite
- [ ] kbtools 的 `create_kb` + `add_document` + `semantic_search` 完整流程
- [ ] 每个模块有基础测试（≥ 80% 覆盖率）
- [ ] Claude Desktop 可连接至少一个模块

### 阶段二：进阶增强版（预计 2-4 周）

> 目标：补全进阶工具 + 完善工程化

| 重点 | 内容 |
|:-----|:-----|
| **补全进阶工具** | `git_diff` / `run_async_command` / `query_with_pagination` |
| **知识库进阶** | BM25 搜索 → 加分项：向量搜索 + 混合搜索 |
| **安全强化** | SQL 语法解析器（用 sqlglot 替代正则） |
| **CI/CD** | GitHub Actions 自动化测试 + PyPI 发布 |
| **Docker** | Dockerfile + docker-compose 编排 |
| **测试覆盖** | 达到阶段目标（安全 100%，其他 ≥90%） |
| **文档** | 完整的 README + docs/ 设计文档 |

### 阶段三：企业级扩展（长线，面试前冲刺）

> 目标：体现"我有持续迭代的能力"

| 重点 | 内容 |
|:-----|:-----|
| **SSE 模式** | 支持 HTTP SSE 网络访问，展示远端服务设计 |
| **多数据源** | PostgreSQL 适配器 |
| **可观测性** | Prometheus 指标暴露 + 健康检查接口 |
| **双语言** | 用 TypeScript 重写一个模块（展示全栈能力） |
| **演示脚本** | 自动化演示脚本，录屏做 GIF |

---

## 11. 面试指南

### 11.1 项目介绍话术（30 秒版）

> *"这是我的 2 号项目 Agent DevTools MCP。它是一个生产级的 MCP 工具网关套件，让 AI Agent 能通过标准协议安全地操作开发工具——文件读写、命令执行、数据库查询、文档搜索。*
>
> *项目采用统一底座 + 三个领域模块的架构，内置三层纵深安全防御体系，所有写入工具默认禁用。测试覆盖率 90% 以上，支持 PyPI 安装和 Docker 部署。*
>
> *它和我 1 号项目的 Agent-CLI 形成完整闭环——Agent-CLI 的 MCP Client 可以直接注册使用这里面所有的工具。"*

### 11.2 面试常见问题

<details>
<summary><b>Q: 为什么选择多包架构而不是单体？</b></summary>

**A:** 三个原因：
1. **职责分离**：每个模块可以独立开发、独立测试、独立部署。加新功能不影响现有功能
2. **面试展示**：这体现了我有架构抽象能力——设计了可复用的 `mcp-common` 公共库，而不是把所有代码堆在一起
3. **渐进开发**：我可以先做完最核心的 devtools 就去求职，dbtools 和 kbtools 后面再补上
</details>

<details>
<summary><b>Q: 你的安全机制是怎么设计的？</b></summary>

**A:** 我设计了**三层纵深防御体系**，而不是零散的校验：
- **第一层 边界防护**：工作区隔离（只能操作指定目录的文件）+ 命令白名单（只允许预设的命令）
- **第二层 操作管控**：路径穿越防护、命令注入防护（全程 shell=False）、SQL 只读校验（参数化查询 + 语法拦截）
- **第三层 审计追溯**：所有操作记录审计日志 + Trace ID 透传

我最自豪的是命令执行安全——所有命令用数组形式 `subprocess.run(["git", "status"])` 执行，从根源上杜绝了 shell 注入攻击。
</details>

<details>
<summary><b>Q: 这个项目和你 1 号项目（Agent-CLI）是什么关系？</b></summary>

**A:** 两者形成完整的技术闭环：
- 1 号项目是 MCP **Client**，实现了 Agent 循环和工具调度
- 2 号项目是 MCP **Server**，提供具体的工具实现

面试时我可以现场演示 Agent-CLI 连接这个 Server，让面试官看到 Agent 自主调用工具的全过程。这证明我不只是理解 MCP 协议的一个方向，而是两端都懂。
</details>

<details>
<summary><b>Q: 文件写入怎么保证安全？</b></summary>

**A:** 三个层面：
1. **原子写入**：用「写临时文件 → fsync → 重命名」的机制，即使写入中途崩溃也不会损坏原文件
2. **默认禁用**：写入工具默认关闭，需要用户在配置中显式启用
3. **路径校验**：所有路径经过 resolve() 规范化，防止路径遍历攻击
</details>

<details>
<summary><b>Q: 项目中用了哪些设计模式？</b></summary>

**A:**
- **策略模式 + 工厂模式**：数据库适配器，加新数据库只需写一个新类
- **模板方法模式**：工具执行流程统一（校验 → 执行 → 日志 → 返回）
- **拦截器模式**：日志、鉴权、限流等横切关注点通过拦截器统一处理
- **适配器模式**：屏蔽不同数据库、不同知识库引擎的底层差异
</details>

### 11.3 演示场景设计

| 场景 | 面试官问法 | 你怎么演示 |
|:-----|:----------|:-----------|
| **文件操作** | "你的 Agent 能读写文件吗？" | 让 Claude 通过 devtools 读取项目文件 → 修改内容 → 写回 |
| **Git 操作** | "能查 Git 状态吗？" | 调 git_status 查看工作区变更 |
| **数据库查询** | "能查数据库吗？" | 调 list_tables 看有哪些表 → execute_select 查询数据 |
| **知识库搜索** | "能搜项目文档吗？" | 先 add_document 导入文档 → semantic_search 搜索 |
| **安全展示** | "安全机制有用吗？" | 尝试路径穿越（../../etc/passwd）→ 被拒绝；尝试命令注入（; rm -rf /）→ 被拒绝 |

---

## 12. 初学者学习路径

> 如果你是第一次做完整的 Python 项目，在学习本项目需要的知识时，按这个顺序来：

### 第一步：打好基础（1-3 天）

| 学习内容 | 要学到什么程度 | 参考资源 |
|:---------|:-------------|:---------|
| Python 类型注解 | 会写 `def foo(x: int) -> str:` | Python 官方文档 typing 模块 |
| pytest 基础 | 会写测试函数、assert、fixture | pytest 官方文档 |
| 虚拟环境 | 会用 `uv venv` / `uv sync` | uv 官方文档 |
| Git 基础 | add / commit / push / branch | GitHub 文档 |

### 第二步：理解核心概念（3-5 天）

| 概念 | 要学到什么程度 | 为什么需要 |
|:-----|:-------------|:-----------|
| **MCP 协议** | 理解 tools/list 和 tools/call 的工作流程 | 这是项目的基础协议 |
| **JSON-RPC** | 理解请求/响应的 JSON 格式 | MCP 基于这个协议 |
| **subprocess** | 会调 `subprocess.run()`，理解 shell=True 和 shell=False 的区别 | devtools 模块核心 |
| **pathlib** | 会用 `Path.resolve()`、`Path.exists()` | 路径校验必备 |
| **Whoosh** | 会创建索引和搜索 | kbtools 模块核心 |

### 第三步：按模块学习（2-4 周）

```
第 1 周: 学 mcp-common 用到的知识
   ├── Python 面向对象（抽象类、继承）
   ├── ContextVar（Trace ID 用）
   └── structlog（结构化日志）

第 2 周: 学 mcp-devtools 用到的知识
   ├── subprocess 深入（超时、环境变量）
   ├── 文件 I/O（临时文件、原子操作）
   └── Git 命令（status、diff）

第 3 周: 学 mcp-dbtools 用到的知识
   ├── SQLite（sqlite3 模块）
   ├── SQL 基础（SELECT）
   └── 参数化查询（防 SQL 注入）

第 4 周: 学 mcp-kbtools 用到的知识
   ├── Whoosh 索引和搜索
   ├── 文本分块算法
   └── BM25 原理（理解即可）
```

### 遇到问题怎么办？

```text
❓ "这个代码跑不起来怎么办？"
   → 仔细看错误信息（Python 的错误信息已经告诉你哪里出错了）
   → 把错误信息复制到搜索引擎或问 AI

❓ "看不懂某个概念"
   → 先跳过，继续往下写代码
   → 很多时候写着写着就理解了

❓ "测试通不过"
   → 检查测试是不是写错了（有时候不是代码的问题，是测试的期望不对）
   → 用 pytest -v -s 看详细信息

❓ "不知道该写什么了"
   → 回头看第 10 章的路线图，看当前到哪个阶段了
   → 每个阶段都有明确的验收标准，照着做就行
```

---

## 附录 A：Makefile 常用命令

```makefile
.PHONY: install test lint typecheck coverage clean build

install:
	uv sync --all-extras

test:
	uv run pytest -v

lint:
	uv run ruff check packages/

typecheck:
	uv run mypy packages/

coverage:
	uv run pytest --cov=packages/ --cov-report=term --cov-report=html

build:
	uv build

clean:
	rm -rf dist/ build/ *.egg-info .coverage htmlcov/

all: lint typecheck test coverage
```

---

> **文档版本**: v2.0.0（重构版）  
> **适用对象**: 项目开发者（初学者 → 进阶）  
> **配套项目**: [Agent-CLI](https://github.com/Mrzhou3000/agent-cli)  
> **下一版本规划**: TypeScript 移植 — 将某个模块用 TypeScript 重写，展示双语言能力
