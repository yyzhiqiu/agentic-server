from __future__ import annotations

import pytest

from app.common.exceptions import AppException
from app.graph.chat_agent.metadata import CHAT_AGENT_METADATA
from app.graph.code_agent.metadata import CODE_AGENT_METADATA
from app.graph.types import AgentDefinition
from app.services.agent_service import AgentService


def _build_service() -> AgentService:
    registry = {
        CHAT_AGENT_METADATA.agent_id: AgentDefinition(
            metadata=CHAT_AGENT_METADATA,
            graph=object(),
        ),
        CODE_AGENT_METADATA.agent_id: AgentDefinition(
            metadata=CODE_AGENT_METADATA,
            graph=object(),
        ),
    }
    return AgentService(agent_registry=registry)


def test_agent_service_lists_registered_metadata() -> None:
    service = _build_service()

    metadata_list = service.list_metadata()

    assert [item.agent_id for item in metadata_list] == ["chat_agent", "code_agent"]
    assert metadata_list[1].capabilities == [
        "code_explain",
        "code_review",
        "code_generation",
    ]


def test_agent_service_returns_single_definition() -> None:
    service = _build_service()

    definition = service.get_definition("chat_agent")

    assert definition.metadata.name == "通用聊天助手"


def test_agent_service_raises_app_exception_for_unknown_agent() -> None:
    service = _build_service()

    with pytest.raises(AppException) as exc_info:
        service.get_definition("missing_agent")

    assert exc_info.value.status_code == 404
    assert exc_info.value.data["agent_id"] == "missing_agent"

