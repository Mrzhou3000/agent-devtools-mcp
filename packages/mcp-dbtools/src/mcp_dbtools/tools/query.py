"""数据库查询工具 —— query / list_tables / describe_table / query_with_pagination

让 AI Agent 能安全地查询数据库。
所有 SQL 经过只读校验，防止写入操作。
"""

from __future__ import annotations

import math
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_common.security.sql_validator import validate_readonly_query, validate_table_name

from ..adapters import BaseAdapter


def _format_table(rows: list[dict[str, Any]]) -> str:
    """将查询结果格式化为表格文本

    Args:
        rows: 查询结果行列表

    Returns:
        格式化的表格字符串
    """
    if not rows:
        return "📭 查询结果为空"

    columns = list(rows[0].keys())
    col_widths = [len(c) for c in columns]

    # 计算列宽
    for row in rows:
        for i, col in enumerate(columns):
            val = str(row.get(col, ""))
            col_widths[i] = max(col_widths[i], len(val))

    # 限制列宽（防输出格式混乱）
    col_widths = [min(w, 40) for w in col_widths]

    # 构建表格
    lines: list[str] = []

    # 表头
    header = "  ".join(c.ljust(w) for c, w in zip(columns, col_widths))
    separator = "  ".join("─" * w for w in col_widths)
    lines.append(f"  {header}")
    lines.append(f"  {separator}")

    # 数据行
    for row in rows:
        vals: list[str] = []
        for i, col in enumerate(columns):
            val = str(row.get(col, ""))
            if len(val) > 40:
                val = val[:37] + "..."
            vals.append(val.ljust(col_widths[i]))
        lines.append(f"  {'  '.join(vals)}")

    return "\n".join(lines)


def register_query_tools(
    mcp: FastMCP,
    adapter: BaseAdapter,
) -> None:
    """注册数据库查询工具到 MCP Server

    Args:
        mcp: FastMCP 实例
        adapter: 数据库适配器实例（策略模式）
    """

    @mcp.tool(description="列出数据库中所有表，返回表名和行数")
    async def list_tables() -> str:
        """列出数据库中所有表"""
        try:
            tables = await adapter.list_tables()
        except Exception as e:
            return f"❌ 获取表列表失败: {e}"

        if not tables:
            return "📭 数据库中没有表"

        lines = [f"📊 共 {len(tables)} 个表\n"]
        for t in tables:
            lines.append(f"  📄 {t.name}")
            lines.append(f"     行数: {t.row_count or '未知'}")
            lines.append(f"     列数: {len(t.columns)}")
            lines.append("")

        return "\n".join(lines).strip()

    @mcp.tool(description="查看指定表的列结构、类型和约束信息")
    async def describe_table(table_name: str) -> str:
        """查看表结构

        Args:
            table_name: 表名
        """
        try:
            validate_table_name(table_name)
            info = await adapter.describe_table(table_name)
        except ValueError as e:
            return f"❌ 非法的表名: {e}"
        except Exception as e:
            return f"❌ 获取表结构失败: {e}"

        lines = [
            f"📄 表: {info.name}",
            f"   行数: {info.row_count or '未知'}",
            f"   列数: {len(info.columns)}",
            "",
            "   列结构:",
            "   ───────",
        ]

        for col in info.columns:
            pk_mark = " 🔑" if col.is_primary_key else ""
            nullable_mark = "" if col.nullable else " NOT NULL"
            default_str = f" DEFAULT {col.default}" if col.default else ""
            lines.append(
                f"   {col.name:20} {col.data_type:15}{nullable_mark}{default_str}{pk_mark}"
            )

        return "\n".join(lines).strip()

    @mcp.tool(description="执行只读 SQL 查询，返回查询结果表格")
    async def query(sql: str) -> str:
        """执行 SQL 查询

        安全限制:
            - 只允许 SELECT / EXPLAIN / DESCRIBE / WITH 等只读语句
            - 禁止 INSERT / UPDATE / DELETE / DROP / ALTER 等写入操作
            - 禁止多语句执行

        Args:
            sql: SQL 查询语句（只读）
        """
        # 1️⃣ SQL 只读校验
        try:
            validate_readonly_query(sql)
        except PermissionError as e:
            return f"❌ SQL 被拒绝: {e}"
        except ValueError as e:
            return f"❌ SQL 校验失败: {e}"

        # 2️⃣ 执行查询
        try:
            rows = await adapter.execute_query(sql)
        except Exception as e:
            return f"❌ 查询执行失败: {e}"

        if not rows:
            return "📭 查询结果为空"

        header = f"📊 查询结果: {len(rows)} 行\n"
        return header + _format_table(rows)

    @mcp.tool(description="分页查询 SQL，支持 page/page_size 参数，同时返回总数")
    async def query_with_pagination(
        sql: str,
        page: int = 1,
        page_size: int = 20,
    ) -> str:
        """分页查询

        自动在 SQL 外层包装 COUNT 和 LIMIT/OFFSET 分页逻辑。
        注意: 原 SQL 不应包含 LIMIT 子句。

        Args:
            sql: SELECT 查询语句（不应包含 LIMIT）
            page: 页码（从 1 开始，默认 1）
            page_size: 每页行数（默认 20，最大 100）
        """
        # 参数校验
        if page < 1:
            return "❌ 页码从 1 开始"
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        # SQL 只读校验
        try:
            validate_readonly_query(sql)
        except (PermissionError, ValueError) as e:
            return f"❌ SQL 被拒绝: {e}"

        try:
            # 获取总数
            count_sql = f"SELECT COUNT(*) AS _total FROM ({sql}) AS _count_sub"
            count_rows = await adapter.execute_query(count_sql)
            total = count_rows[0]["_total"] if count_rows else 0

            # 获取分页数据
            page_sql = f"{sql.rstrip(';')} LIMIT {page_size} OFFSET {offset}"
            rows = await adapter.execute_query(page_sql)
        except Exception as e:
            return f"❌ 分页查询失败: {e}"

        # 格式化输出
        total_pages = max(1, math.ceil(total / page_size))

        lines = [
            "📊 分页查询结果",
            f"  总行数: {total}",
            f"  当前页: {page}/{total_pages}",
            f"  每页行数: {page_size}",
            f"  当前页行数: {len(rows)}",
            "",
        ]

        if rows:
            lines.append(_format_table(rows))

        return "\n".join(lines)
