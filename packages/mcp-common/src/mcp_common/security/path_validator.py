"""路径校验器 —— 防止路径遍历攻击（Path Traversal）

工作原理:
    用户传入一个相对路径（如 "../../etc/passwd"），
    我们把它拼接到工作目录后面，然后用 resolve() 解析真实的绝对路径，
    最后检查这个路径是否在工作目录内。

    ✅ 允许: 用户传 "src/server.py" → 解析为 /workspace/src/server.py → 在工作目录内
    ❌ 拒绝: 用户传 "../../etc/passwd" → 解析为 /etc/passwd → 不在工作目录内

用法:
    validator = PathValidator(workspace_root="/home/user/projects")
    safe_path = validator.validate("src/server.py")   # 返回 Path 对象
    # safe_path == /home/user/projects/src/server.py
"""

from __future__ import annotations

from pathlib import Path


class PathTraversalError(PermissionError):
    """路径遍历攻击被拦截时抛出的异常"""

    def __init__(self, original_path: str, resolved_path: Path, workspace: Path):
        self.original_path = original_path
        self.resolved_path = resolved_path
        self.workspace = workspace
        super().__init__(
            f"路径越权: '{original_path}' 解析为 '{resolved_path}'，不在工作目录 '{workspace}' 内"
        )


class PathValidator:
    """路径校验器 —— 所有文件操作工具的安全守卫"""

    def __init__(self, workspace_root: str | Path) -> None:
        """
        Args:
            workspace_root: 允许操作的工作目录绝对路径
                            （所有文件操作限制在这个目录内）
        """
        self.workspace_root = Path(workspace_root).resolve()

    def validate(self, target_path: str) -> Path:
        """校验并返回安全的绝对路径

        Args:
            target_path: 用户传入的文件路径（相对路径）

        Returns:
            解析后的绝对路径 Path 对象

        Raises:
            PathTraversalError: 如果路径解析后不在工作目录内
            ValueError: 如果 target_path 为空

        校验流程:
            1. 拼接工作目录和用户路径
            2. 用 resolve() 解析真实路径（处理 '..' 和软链接）
            3. 检查解析后的路径是否以 workspace_root 开头
        """
        # 空路径检查
        if not target_path or not target_path.strip():
            raise ValueError("路径不能为空")

        # 去掉首尾空格，但保留路径中的空格
        target_path = target_path.strip()

        # 拼接并解析绝对路径
        # Path("/workspace") / "../../etc/passwd" → /workspace/../../etc/passwd
        # .resolve() → /etc/passwd（解析 .. 和软链接）
        resolved = (self.workspace_root / target_path).resolve()

        # 核心检查：解析后的路径必须在工作目录内
        # 把路径转为字符串比较，确保是前缀匹配（不是字符串包含）
        resolved_str = str(resolved)
        workspace_str = str(self.workspace_root)

        if not resolved_str.startswith(workspace_str):
            raise PathTraversalError(target_path, resolved, self.workspace_root)

        return resolved

    def validate_file(self, target_path: str) -> Path:
        """校验路径，且必须是一个存在的文件

        在 validate() 的基础上，增加文件存在性检查
        """
        path = self.validate(target_path)
        if not path.is_file():
            raise FileNotFoundError(f"文件不存在: {target_path}")
        return path

    def validate_directory(self, target_path: str) -> Path:
        """校验路径，且必须是一个存在的目录"""
        path = self.validate(target_path)
        if not path.is_dir():
            raise NotADirectoryError(f"目录不存在: {target_path}")
        return path
