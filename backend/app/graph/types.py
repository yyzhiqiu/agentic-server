"""Agent 注册表相关通用类型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


AgentId = str
"""对外暴露的 Agent 唯一标识。"""


@dataclass(slots=True)
class AgentMetadata:
    """对外暴露的 Agent 元信息。"""

    agent_id: AgentId
    name: str
    description: str
    version: str
    capabilities: list[str]


@dataclass(slots=True)
class AgentDefinition:
    """注册表中的 Agent 定义。

    一个 ``AgentDefinition`` 对应一个可被外部选择调用的独立 Agent graph。
    graph 的构建与编译发生在启动阶段，而不是请求处理期间。
    """

    metadata: AgentMetadata
    graph: Any


AgentRegistry = dict[AgentId, AgentDefinition]
"""应用启动后保存在 ``app.state`` 中的 Agent 注册表。"""

