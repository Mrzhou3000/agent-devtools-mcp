# Agent DevTools MCP — Claude 开发约定

## Git 工作流

当我说"执行约定的 git 工作流"或类似表达时，请自动执行以下流程：

### 步骤 1：暂存与 Pre-commit

```bash
# 添加变更文件（按变更聚焦选择，不加多余文件）
git add <聚焦的文件>

# 运行 pre-commit 检查全部钩子
pre-commit run
```

- 如果 pre-commit 失败，**自动修复**问题后重新 `git add` 再跑，直到通过
- 常见的修复：Ruff 自动格式化、mypy 类型注解补全
- 每个 commit **只聚焦一个变更主题**，保持颗粒度合适

### 步骤 2：提交

```bash
# 使用约定式提交格式
git commit -m "类型: 简短描述

- 详细变更点（按需）"
```

提交类型：`feat` / `fix` / `refactor` / `test` / `docs` / `chore` / `style`

### 步骤 3：推送

```bash
git push
```

### 步骤 4：检查 CI

推送后自动检查 GitHub Actions 是否通过：

```bash
# 查看 CI 运行状态
gh run list --limit 3 --workflow=CI

# 如果 CI 正在运行，等待结果
gh run watch

# 如果 CI 失败，查看失败详情并修复
gh run view --log-failed
```

- 如果 CI 失败，分析日志、修复问题、重新 commit → push
- 直到 CI 全部通过为止

### 前置条件

- 需要已安装 `pre-commit`（`pip install pre-commit && pre-commit install`）
- 需要 `gh`（GitHub CLI）已登录认证
