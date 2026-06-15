"""公共数据模型 —— 各模块共用的基础类型

所有 MCP 工具返回结果统一使用 ToolResult 包装，
确保输出格式一致。

用法:
    from mcp_common.models.base import ToolResult

    return ToolResult.success("操作成功")
    return ToolResult.error("操作失败", code="COM_EXE_001")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class BaseModel:
    """所有数据模型的基类"""

    def to_dict(self) -> dict[str, Any]:
        """转为字典（用于序列化）"""
        result: dict[str, Any] = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if hasattr(value, "to_dict"):
                result[field_name] = value.to_dict()
            elif isinstance(value, list):
                result[field_name] = [
                    v.to_dict() if hasattr(v, "to_dict") else v
                    for v in value
                ]
            else:
                result[field_name] = value
        return result


@dataclass
class ToolResult(BaseModel):
    """统一的工具调用结果

    Attributes:
        success: 是否成功
        data: 返回数据（成功时）
        message: 用户可读的消息
        code: 错误码（失败时）
        suggestion: 解决建议（失败时）
    """

    success: bool = True
    data: Any = None
    message: str = ""
    code: str = ""
    suggestion: str = ""

    @classmethod
    def ok(cls, message: str = "", data: Any = None) -> ToolResult:
        """创建成功结果"""
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(
        cls,
        message: str,
        code: str = "",
        suggestion: str = "",
        data: Any = None,
    ) -> ToolResult:
        """创建失败结果"""
        return cls(
            success=False,
            message=message,
            code=code,
            suggestion=suggestion,
            data=data,
        )

    def __str__(self) -> str:
        if self.success:
            return self.message or "操作成功"
        parts = [f"❌ {self.message}"]
        if self.suggestion:
            parts.append(f"💡 {self.suggestion}")
        return "\n".join(parts)


@dataclass
class PaginatedResult(BaseModel, Generic[T]):
    """分页查询结果

    Attributes:
        items: 当前页数据
        total: 总记录数
        page: 当前页码（从 1 开始）
        page_size: 每页大小
        has_more: 是否还有更多数据
    """

    items: list[T] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20

    @property
    def has_more(self) -> bool:
        return self.page * self.page_size < self.total

    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)
