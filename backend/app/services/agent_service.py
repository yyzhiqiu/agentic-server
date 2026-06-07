"""Agent 注册表访问服务。

本服务负责封装 ``app.state.agent_registry`` 的读取与校验逻辑，让 API 层不直接操作
注册表内部结构。它不管理事务，也不依赖数据库。
"""

from __future__ import annotations

from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.graph.types import AgentDefinition, AgentRegistry
from app.schemas.agent import AgentMetadataResponse


class AgentService:
    """Agent 注册表访问服务。"""

    def __init__(self, *, agent_registry: AgentRegistry) -> None:
        self.agent_registry = agent_registry

    @staticmethod
    def _to_metadata_response(definition: AgentDefinition) -> AgentMetadataResponse:
        """将注册表中的 AgentDefinition 转换为 API 响应 Schema。"""

        metadata = definition.metadata
        return AgentMetadataResponse(
            agent_id=metadata.agent_id,
            name=metadata.name,
            description=metadata.description,
            version=metadata.version,
            capabilities=list(metadata.capabilities),
        )

    def list_metadata(self) -> list[AgentMetadataResponse]:
        """列出当前服务对外暴露的全部 Agent 元信息。"""

        return [
            self._to_metadata_response(definition)
            for definition in self.agent_registry.values()
        ]

    def get_definition(self, agent_id: str) -> AgentDefinition:
        """根据 ``agent_id`` 获取一个已注册 Agent 的完整定义。

        Raises:
            AppException: 当 ``agent_id`` 不存在时抛出统一的项目异常。
        """

        definition = self.agent_registry.get(agent_id)
        if definition is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                message="指定的 Agent 不存在",
                status_code=404,
                data={"agent_id": agent_id},
            )
        return definition

    def get_metadata(self, agent_id: str) -> AgentMetadataResponse:
        """获取单个 Agent 的对外元信息。"""

        return self._to_metadata_response(self.get_definition(agent_id))

