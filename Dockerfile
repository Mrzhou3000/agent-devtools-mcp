FROM python:3.12-slim

LABEL org.opencontainers.image.title="Agent DevTools MCP"
LABEL org.opencontainers.image.description="生产级 MCP 工具网关套件 —— 为 AI Agent 提供开发工具/数据库/知识库调用能力"
LABEL org.opencontainers.image.version="0.1.0"

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install --no-cache-dir uv

# 复制项目文件
WORKDIR /app
COPY . .

# 安装项目依赖
RUN uv sync --no-dev

# 默认工作目录（供 devtools 使用）
VOLUME ["/workspace"]

# 默认命令：显示帮助信息
ENTRYPOINT ["uv", "run", "--package"]
CMD ["mcp-devtools", "python", "-m", "mcp_devtools", "run", "--help"]
