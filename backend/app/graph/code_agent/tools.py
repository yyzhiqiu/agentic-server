"""代码助手 Agent 的专属工具定义。"""

from __future__ import annotations

from app.graph.shared.tools import calculator_tool, file_tool, search_tool


def get_code_agent_tools() -> list:
    """返回代码助手 Agent 当前启用的专属工具集合。

    当前阶段仍然坚持只读、低副作用策略，因此只暴露搜索、文件占位与简单计算
    能力，不默认开放终端、Git 或文件写入能力。
    """

    return [search_tool, file_tool, calculator_tool]
