# 部署指南

## 本地开发

```bash
# 安装依赖
uv sync

# 启动 devtools
uv run --package mcp-devtools python -m mcp_devtools run

# 启动 dbtools
uv run --package mcp-dbtools python -m mcp_dbtools run --database ./test.db

# 启动 kbtools
uv run --package mcp-kbtools python -m mcp_kbtools run
```

## Claude Desktop

在 `claude_desktop_config.json` 中配置（参见 examples/）：

```json
{
  "mcpServers": {
    "devtools": { "command": "uv", "args": ["run", "--package", "mcp-devtools", "python", "-m", "mcp_devtools", "run", "--workspace", "."] },
    "dbtools": { "command": "uv", "args": ["run", "--package", "mcp-dbtools", "python", "-m", "mcp_dbtools", "run", "--database", "./test.db"] },
    "kbtools": { "command": "uv", "args": ["run", "--package", "mcp-kbtools", "python", "-m", "mcp_kbtools", "run"] }
  }
}
```

## Docker

```bash
# 构建
docker build -t agent-devtools-mcp .

# 运行 devtools
docker run -v /path/to/workspace:/workspace agent-devtools-mcp \
    mcp-devtools python -m mcp_devtools run --workspace /workspace
```

## 环境变量配置

| 变量 | 说明 | 默认值 |
|:-----|:-----|:-------|
| MCP_DEVTOOLS__ALLOW_WRITE | 允许写入 | false |
| MCP_DEVTOOLS__ALLOW_COMMAND | 允许命令执行 | false |
| MCP_DATABASE__MAX_ROWS | 最大查询行数 | 1000 |
| MCP_DATABASE__READ_ONLY | 只读模式 | true |
