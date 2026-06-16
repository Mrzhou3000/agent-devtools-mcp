"""命令执行工具 —— run_command / run_async_command / git_status / git_diff

让 AI Agent 能在工作目录内安全执行命令（如 git、python、uv 等）。

安全设计:
    - 命令白名单（只允许预设的安全命令）
    - 参数检测（拒绝危险字符: ; ` $ | && || 等）
    - 超时机制（防止命令卡死）
    - 输出限制（防止输出撑爆内存）
    - 完整审计日志
"""

from __future__ import annotations

import asyncio
import shlex
import uuid
from dataclasses import dataclass, field
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_common.security.sandbox import Sandbox

# 默认超时时间（30 秒）
DEFAULT_TIMEOUT = 30

# 最大输出大小（1MB）
MAX_OUTPUT_SIZE = 1024 * 1024

# 默认工作目录
DEFAULT_WORK_DIR = "."


def register_command_tools(
    mcp: FastMCP,
    sandbox: Sandbox,
) -> None:
    """注册命令执行工具到 MCP Server

    Args:
        mcp: FastMCP 实例
        sandbox: 安全沙箱实例
    """

    # ═══════════════════════════════════════════════════════════
    # 异步任务管理
    # ═══════════════════════════════════════════════════════════

    @dataclass
    class AsyncTask:
        """异步任务记录"""
        task_id: str
        command: str
        status: str = "running"  # running / done / error
        stdout: str = ""
        stderr: str = ""
        return_code: int | None = None
        error: str = ""

    _async_tasks: dict[str, AsyncTask] = {}

    async def _run_async_command_internal(
        command: str,
        args: list[str],
        work_dir: str,
        timeout: int,
        sandbox: Sandbox,
        task_id: str,
    ) -> None:
        """在后台执行命令（内部函数）"""
        task = _async_tasks[task_id]
        try:
            safe_work_dir = sandbox.validate_path(work_dir)
            proc = await asyncio.create_subprocess_exec(
                command, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(safe_work_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout,
            )
            task.stdout = stdout.decode("utf-8", errors="replace")
            task.stderr = stderr.decode("utf-8", errors="replace")
            task.return_code = proc.returncode
            task.status = "done"
        except asyncio.TimeoutError:
            task.status = "error"
            task.error = f"执行超时（{timeout}秒）"
        except Exception as e:
            task.status = "error"
            task.error = str(e)

    @mcp.tool(
        description="异步执行耗时命令（如安装依赖、构建项目），立即返回任务 ID。默认禁用，需配置 allow_command=true"
    )
    async def run_async_command(
        command: str,
        args: str = "",
        work_dir: str = ".",
        timeout: int = 300,
    ) -> str:
        """异步执行命令

        适用于构建、安装等耗时命令。立即返回任务 ID，
        后续可通过 get_async_result 查询执行结果。

        Args:
            command: 命令名称（必须在允许的白名单内）
            args: 命令参数（以空格分隔的字符串）
            work_dir: 工作目录（相对于 workspace_root）
            timeout: 超时时间（秒，默认 300）
        """
        try:
            sandbox.validate_path(work_dir)
            parsed_args = shlex.split(args) if args else []
            sandbox.validate_command(command, parsed_args)
        except PermissionError as e:
            return f"❌ 命令被拒绝: {e}"

        task_id = f"async_{uuid.uuid4().hex[:8]}"
        _async_tasks[task_id] = AsyncTask(task_id=task_id, command=command)

        # 在后台启动
        asyncio.ensure_future(_run_async_command_internal(
            command=command,
            args=parsed_args,
            work_dir=work_dir,
            timeout=timeout,
            sandbox=sandbox,
            task_id=task_id,
        ))

        return (
            f"✅ 异步任务已启动\n"
            f"  任务 ID: {task_id}\n"
            f"  命令: {command} {args}\n"
            f"  💡 使用 get_async_result 查询结果，任务 ID: {task_id}"
        )

    @mcp.tool(description="查询异步命令的执行结果，通过 run_async_command 返回的任务 ID 查询")
    async def get_async_result(
        task_id: str,
    ) -> str:
        """查询异步命令执行结果

        Args:
            task_id: run_async_command 返回的任务 ID
        """
        task = _async_tasks.get(task_id)
        if task is None:
            return f"❌ 任务不存在: {task_id}"

        if task.status == "running":
            return f"⏳ 任务 {task_id} 正在执行中，请稍后再查"

        if task.status == "error":
            return f"❌ 任务 {task_id} 执行失败: {task.error}"

        # 构建结果输出
        result_parts = []
        if task.stdout:
            result_parts.append(task.stdout)
        if task.stderr:
            if task.stdout:
                result_parts.append("")
            result_parts.append(f"⚠️ stderr:\n{task.stderr}")
        if task.return_code is not None and task.return_code != 0:
            result_parts.append(f"⚠️ 退出码: {task.return_code}")

        return "\n".join(result_parts) if result_parts else "(无输出)"

    # ── run_command ────────────────────────────────────────────

    @mcp.tool(
        description=(
            "在工作目录内执行命令。"
            "只能执行白名单内的安全命令: git, python, uv, pip, ls, cat, pwd, echo 等。"
            "返回命令的输出内容（stdout + stderr）。"
        )
    )
    async def run_command(
        command: str,
        args: str = "",
        work_dir: str = ".",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """执行命令

        Args:
            command: 命令名称（必须在允许的白名单内）
            args: 命令参数（以空格分隔的字符串）
            work_dir: 工作目录（相对于 workspace_root，默认为 "."）
            timeout: 超时时间（秒，默认 30）
        """
        import time
        start_time = time.time()

        try:
            # 1️⃣ 验证工作目录
            try:
                safe_work_dir = sandbox.validate_path(work_dir)
            except PermissionError as e:
                return f"❌ 路径越权: {e}"

            # 2️⃣ 安全校验：命令白名单 + 参数危险字符检测
            parsed_args = shlex.split(args) if args else []
            try:
                sandbox.validate_command(command, parsed_args)
            except PermissionError as e:
                return f"❌ 命令被拒绝: {e}"

            # 3️⃣ 执行命令（shell=False 防注入）
            proc = await asyncio.create_subprocess_exec(
                command,
                *parsed_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(safe_work_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            # 4️⃣ 输出限制
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if len(stdout_str) > MAX_OUTPUT_SIZE:
                stdout_str = stdout_str[:MAX_OUTPUT_SIZE] + "\n... (输出截断)"
            if len(stderr_str) > MAX_OUTPUT_SIZE:
                stderr_str = stderr_str[:MAX_OUTPUT_SIZE] + "\n... (输出截断)"

            # 5️⃣ 构建返回结果
            result_parts = []
            if stdout_str:
                result_parts.append(stdout_str)
            if stderr_str:
                if stdout_str:
                    result_parts.append("")
                result_parts.append(stderr_str)
            if proc.returncode != 0:
                result_parts.append(f"\n⚠️ 命令退出码: {proc.returncode}")

            duration = time.time() - start_time

            # 6️⃣ 审计日志
            sandbox.log_call(
                "run_command",
                {"command": command, "args": args, "work_dir": work_dir},
                status="success" if proc.returncode == 0 else "warning",
                duration_ms=int(duration * 1000),
            )

            return "\n".join(result_parts) if result_parts else "(无输出)"

        except asyncio.TimeoutError:
            return (
                f"❌ 命令执行超时（{timeout}秒）\n"
                f"💡 可通过 timeout 参数调整超时时间"
            )
        except FileNotFoundError:
            return (
                f"❌ 命令未找到: '{command}'\n"
                f"💡 请检查命令是否已安装\n"
                f"💡 允许的命令: {', '.join(sorted(sandbox.command_validator.allowed_commands))}"
            )
        except Exception as e:
            return f"❌ 命令执行失败: {e}"

    @mcp.tool(description="查看 Git 仓库状态（git status），返回简洁的状态概览")
    async def git_status(
        work_dir: str = ".",
    ) -> str:
        """查看 Git 仓库状态

        相当于执行 `git status --short`，返回简洁的状态信息。

        Args:
            work_dir: Git 仓库路径（相对于 workspace_root）
        """
        try:
            safe_path = sandbox.validate_path(work_dir)
        except PermissionError as e:
            return f"❌ 路径越权: {e}"

        # 检查是否是 Git 仓库
        git_dir = safe_path / ".git"
        if not git_dir.exists():
            return (
                f"❌ 不是 Git 仓库: '{work_dir}'\n"
                f"💡 当前目录没有 .git 目录"
            )

        git_path = _find_git()
        if git_path is None:
            return "❌ 未找到 git 命令"

        proc = await asyncio.create_subprocess_exec(
            git_path, "status", "--short",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(safe_path),
        )
        stdout, stderr = await proc.communicate()

        output = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            return f"❌ git status 失败: {err}"

        if not output.strip():
            return "✅ 工作区干净，无未提交的更改"

        # 统计变更类型
        lines = [line for line in output.strip().split("\n") if line.strip()]
        staged = sum(1 for ln in lines if not ln[1].strip() or ln[0] != " ")
        unstaged = sum(1 for ln in lines if ln[1] != " ")
        untracked = sum(1 for ln in lines if ln[:2] == "??")

        summary_parts = [f"📊 共 {len(lines)} 个变更"]
        if staged:
            summary_parts.append(f"  已暂存: {staged}")
        if unstaged:
            summary_parts.append(f"  未暂存: {unstaged}")
        if untracked:
            summary_parts.append(f"  未跟踪: {untracked}")

        return (
            f"{' | '.join(summary_parts)}\n"
            f"───\n"
            f"{output}"
        )

    @mcp.tool(description="查看 Git 差异（git diff），显示工作区和暂存区的变更内容")
    async def git_diff(
        target: str = "",
        work_dir: str = ".",
        max_lines: int = 200,
    ) -> str:
        """查看 Git 差异

        Args:
            target: 差异目标（为空则显示工作区 vs 暂存区，也可指定提交哈希或分支名）
            work_dir: Git 仓库路径（相对于 workspace_root）
            max_lines: 最大输出行数（默认 200，防输出过大）
        """
        try:
            safe_path = sandbox.validate_path(work_dir)
        except PermissionError as e:
            return f"❌ 路径越权: {e}"

        git_dir = safe_path / ".git"
        if not git_dir.exists():
            return f"❌ 不是 Git 仓库: '{work_dir}'"

        git_path = _find_git()
        if git_path is None:
            return "❌ 未找到 git 命令"

        args = ["diff", "--color=never"]
        if target:
            args.append(target)

        proc = await asyncio.create_subprocess_exec(
            git_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(safe_path),
        )
        stdout, stderr = await proc.communicate()

        output = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            return f"❌ git diff 失败: {err}"

        if not output.strip():
            return "📭 没有差异"

        lines = output.split("\n")
        if len(lines) > max_lines:
            # 保留前 max_lines 行
            output = "\n".join(lines[:max_lines])
            output += f"\n\n... (输出截断，共 {len(lines)} 行，只显示前 {max_lines} 行)"
            output += "\n💡 可通过 max_lines 参数调整限制"

        return output


def _find_git() -> str | None:
    """查找系统中的 git 可执行文件"""
    import shutil
    return shutil.which("git")
