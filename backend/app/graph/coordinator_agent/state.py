"""协调入口 Agent 的图状态定义。"""

from __future__ import annotations

from typing import Any

from app.graph.shared.state import BaseAgentState


class CoordinatorAgentState(BaseAgentState, total=False):
    """描述协调入口 Agent 在单次图执行中的共享状态字段。"""

    route_intent: str
    target_agent_id: str
    route_result: dict[str, Any] | None
    route_request_text: str
    origin_text: str | None
    destination_text: str | None
    destination_city_hint: str | None
    travel_mode: str | None
    missing_fields: list[str]
    validation_errors: dict[str, str]
    pending_human_input: dict[str, Any] | None
    resolved_origin: dict[str, Any] | None
    resolved_destination: dict[str, Any] | None
    route_plan: dict[str, Any] | None
    tool_calls: list[dict[str, Any]]
