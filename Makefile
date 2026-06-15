.PHONY: install dev test lint typecheck coverage clean build docker

# ── 安装 ────────────────────────────────────────────────────

install:
	uv sync --all-extras

dev:
	uv sync --all-extras --dev

# ── 测试 ─────────────────────────────────────────────────────

test:
	uv run pytest -v

test-coverage:
	uv run pytest --cov=packages/ --cov-report=term --cov-report=html

test-quick:
	uv run pytest -x -q

# ── 代码质量 ────────────────────────────────────────────────

lint:
	uv run ruff check packages/ --fix

typecheck:
	uv run mypy packages/

format:
	uv run ruff format packages/

# ── 构建与清理 ──────────────────────────────────────────────

build:
	uv build

clean:
	rm -rf dist/ build/ *.egg-info .coverage htmlcov/ .mypy_cache/ .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# ── Docker ──────────────────────────────────────────────────

docker:
	docker build -t agent-devtools-mcp .

# ── 全量检查 ────────────────────────────────────────────────

all: format lint typecheck test-coverage
	@echo "✅ 全部检查通过"
