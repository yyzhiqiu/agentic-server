"""多个 Agent 共享的简单计算器工具。"""

from __future__ import annotations


async def calculator_tool(expression: str) -> dict:
    """在受限上下文中计算简单表达式。

    注意：
        这里只允许使用空 ``__builtins__`` 的极简 ``eval``，用于脚手架级演示。
        如果后续要接入真实生产能力，应替换为更明确、安全的表达式解析器。
    """

    try:
        value = eval(expression, {"__builtins__": {}}, {})
    except Exception as exc:
        return {"expression": expression, "error": str(exc)}
    return {"expression": expression, "value": value}

