"""协调入口 Agent 的节点实现。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.graph.chat_agent.nodes import create_chat_agent_node
from app.graph.coordinator_agent.state import CoordinatorAgentState
from app.graph.route_planner_agent.nodes import (
    _extract_route_fields,
    create_execute_route_plan_node,
    create_prepare_human_interaction_node,
    create_resume_merge_node,
    create_summarize_route_result_node,
    create_validate_route_slots_node,
)
from app.graph.shared.messages import read_message_content, read_message_metadata, read_message_role
from app.graph.shared.nodes.human_interaction import create_human_interaction_node
from app.integrations.amap_mcp import AmapRouteToolset
from app.observability.decorators import observe_node

logger = logging.getLogger(__name__)

ROUTE_KEYWORDS = (
    "路线",
    "导航",
    "怎么走",
    "怎么去",
    "出行方式",
    "驾车",
    "开车",
    "自驾",
    "步行",
    "公交",
    "地铁",
)

ROUTE_PATTERNS = (
    re.compile(r"从.+到.+"),
    re.compile(r"(我要|我想|想|准备|计划|打算|帮我|请帮我).{0,12}(去|到).+"),
    re.compile(r"(去|到).+(怎么去|怎么走|路线|导航)"),
)

TRAVEL_MODE_ALIASES = {
    "driving": "driving",
    "drive": "driving",
    "car": "driving",
    "驾车": "driving",
    "开车": "driving",
    "自驾": "driving",
    "walking": "walking",
    "walk": "walking",
    "步行": "walking",
    "走路": "walking",
    "transit": "transit",
    "bus": "transit",
    "公交": "transit",
    "地铁": "transit",
    "公共交通": "transit",
}

STRUCTURED_ROUTE_FIELD_ALIASES = {
    "origin": "origin_text",
    "origin_text": "origin_text",
    "起点": "origin_text",
    "出发地": "origin_text",
    "出发位置": "origin_text",
    "destination": "destination_text",
    "destination_text": "destination_text",
    "终点": "destination_text",
    "目的地": "destination_text",
    "travel_mode": "travel_mode",
    "travelMode": "travel_mode",
    "出行方式": "travel_mode",
    "交通方式": "travel_mode",
    "方式": "travel_mode",
    "destination_city_hint": "destination_city_hint",
    "destinationCityHint": "destination_city_hint",
    "终点所在城市": "destination_city_hint",
    "目的地城市": "destination_city_hint",
}

ROUTE_DECISION_SYSTEM_PROMPT = """你是多智能体系统的入口协调器，只负责判断本轮对话应该分发到哪个智能体。

可选分支：
1. general_chat：通用问答、解释、闲聊、代码以外的普通咨询。
2. route_planning：用户表达要前往某地、询问路线/导航/怎么走/怎么去，或在既有路线规划上下文中补充/继续规划。

判断要求：
- 必须结合最近多轮上下文，不要只看最后一句关键词。
- “从产品角度”“到目前为止”这类非出行语义不要分到 route_planning。
- 如果用户只是问旅游推荐、美食、城市介绍，且没有要求规划怎么去，分到 general_chat。
- 如果用户说“我要去广东”“帮我规划路线”“从南京到西安怎么走”等出行意图，分到 route_planning。
- 只输出 JSON，不要输出 Markdown。

JSON 格式：
{"intent":"general_chat|route_planning","confidence":0.0,"reason":"一句中文原因"}"""


def _last_user_message(state: CoordinatorAgentState) -> str:
    """提取当前状态中的最后一条用户消息。"""

    for message in reversed(state.get("messages", [])):
        if read_message_role(message) == "user":
            return read_message_content(message).strip()
    return ""


def _recent_conversation_context(state: CoordinatorAgentState, *, limit: int = 8) -> str:
    """把最近多轮消息整理为 LLM 路由可读的上下文。"""

    lines: list[str] = []
    for message in state.get("messages", [])[-limit:]:
        role = read_message_role(message)
        content = read_message_content(message).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        role_label = "用户" if role == "user" else "助手"
        lines.append(f"{role_label}: {content}")
    return "\n".join(lines)


def _looks_like_route_request(text: str) -> bool:
    """在 LLM 不可用时用较高置信度规则兜底判断路线意图。"""

    if not text:
        return False
    if any(keyword in text for keyword in ROUTE_KEYWORDS):
        return True
    return any(pattern.search(text) is not None for pattern in ROUTE_PATTERNS)


def _normalize_text_slot(value: Any) -> str | None:
    """把槽位值规整为可复用的非空文本。"""

    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_travel_mode(value: Any) -> str | None:
    """把中英文出行方式别名规整为内部枚举。"""

    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return TRAVEL_MODE_ALIASES.get(normalized)


def _apply_route_slot(
    slots: dict[str, str | None],
    key: str,
    value: Any,
) -> None:
    """把一个候选槽位写入临时上下文，空值不会覆盖已有值。"""

    if key == "travel_mode":
        normalized_travel_mode = _normalize_travel_mode(value)
        if normalized_travel_mode is not None:
            slots[key] = normalized_travel_mode
        return

    normalized_text = _normalize_text_slot(value)
    if normalized_text is not None:
        slots[key] = normalized_text


def _extract_structured_route_fields_from_mapping(payload: dict[str, Any]) -> dict[str, str | None]:
    """从补参 payload 的字段名中提取路线槽位。"""

    slots: dict[str, str | None] = {
        "origin_text": None,
        "destination_text": None,
        "destination_city_hint": None,
        "travel_mode": None,
    }
    for raw_key, value in payload.items():
        if not isinstance(raw_key, str):
            continue
        normalized_key = raw_key.strip()
        slot_key = STRUCTURED_ROUTE_FIELD_ALIASES.get(normalized_key)
        if slot_key is None:
            continue
        _apply_route_slot(slots, slot_key, value)
    return slots


def _extract_structured_route_fields_from_text(text: str) -> dict[str, str | None]:
    """解析“补充路线规划信息：起点：南京；出行方式：driving”这类展示消息。"""

    slots: dict[str, str | None] = {
        "origin_text": None,
        "destination_text": None,
        "destination_city_hint": None,
        "travel_mode": None,
    }
    normalized = text.strip()
    if not normalized:
        return slots

    payload_text = normalized
    for prefix in ("补充路线规划信息", "路线规划信息", "补充信息"):
        if not normalized.startswith(prefix):
            continue
        payload_text = normalized.removeprefix(prefix).lstrip(" ：:")
        break

    for part in re.split(r"[；;\n，,]", payload_text):
        label, separator, value = part.partition("：")
        if not separator:
            label, separator, value = part.partition(":")
        if not separator:
            continue

        slot_key = STRUCTURED_ROUTE_FIELD_ALIASES.get(label.strip())
        if slot_key is None:
            continue
        _apply_route_slot(slots, slot_key, value)
    return slots


def _extract_route_fields_from_message(message: Any) -> dict[str, str | None]:
    """从单条用户消息的元数据、结构化文本和自然语言中抽取路线槽位。"""

    slots: dict[str, str | None] = {
        "origin_text": None,
        "destination_text": None,
        "destination_city_hint": None,
        "travel_mode": None,
    }

    metadata = read_message_metadata(message)
    raw_resume_input = metadata.get("resume_input")
    if not isinstance(raw_resume_input, dict):
        raw_resume_input = metadata.get("resumeInput")
    if isinstance(raw_resume_input, dict):
        for key, value in _extract_structured_route_fields_from_mapping(raw_resume_input).items():
            _apply_route_slot(slots, key, value)

    content = read_message_content(message)
    for key, value in _extract_structured_route_fields_from_text(content).items():
        _apply_route_slot(slots, key, value)

    origin_text, destination_text, travel_mode = _extract_route_fields(content)
    _apply_route_slot(slots, "origin_text", origin_text)
    _apply_route_slot(slots, "destination_text", destination_text)
    _apply_route_slot(slots, "travel_mode", travel_mode)
    return slots


def _merge_route_slots(
    target: dict[str, str | None],
    source: dict[str, str | None],
) -> None:
    """把非空路线槽位合并到目标上下文中。"""

    for key, value in source.items():
        _apply_route_slot(target, key, value)


def _state_route_slots(state: CoordinatorAgentState) -> dict[str, str | None]:
    """读取 checkpoint 中已经确认过的路线槽位。"""

    slots: dict[str, str | None] = {
        "origin_text": None,
        "destination_text": None,
        "destination_city_hint": None,
        "travel_mode": None,
    }
    for key in slots:
        _apply_route_slot(slots, key, state.get(key))
    return slots


def _extract_route_fields_from_context(
    state: CoordinatorAgentState,
) -> tuple[str | None, str | None, str | None, str | None]:
    """从 checkpoint 与最近用户消息中提取路线槽位，支持延续式上下文。

    Why:
        人机补参恢复时，真实可继续执行的起点/方式保存在图状态里；
        前端展示用的“补充路线规划信息”消息不一定会回写到 LangGraph
        消息列表。因此这里先读取历史消息，再用 checkpoint 槽位作为
        已确认事实，最后让最新用户输入覆盖目的地等显式变更。
    """

    slots: dict[str, str | None] = {
        "origin_text": None,
        "destination_text": None,
        "destination_city_hint": None,
        "travel_mode": None,
    }

    user_messages = [
        message
        for message in state.get("messages", [])
        if read_message_role(message) == "user"
    ]
    for message in user_messages[:-1]:
        _merge_route_slots(slots, _extract_route_fields_from_message(message))

    _merge_route_slots(slots, _state_route_slots(state))

    if user_messages:
        _merge_route_slots(slots, _extract_route_fields_from_message(user_messages[-1]))

    return (
        slots["origin_text"],
        slots["destination_text"],
        slots["destination_city_hint"],
        slots["travel_mode"],
    )


def _parse_llm_route_decision(content: str) -> dict[str, Any] | None:
    """解析 LLM 返回的路由 JSON。"""

    normalized = content.strip()
    match = re.search(r"\{.*\}", normalized, flags=re.S)
    if match is not None:
        normalized = match.group(0)

    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    intent = payload.get("intent")
    if intent not in {"general_chat", "route_planning"}:
        return None

    confidence = payload.get("confidence")
    if not isinstance(confidence, int | float):
        confidence = None

    reason = payload.get("reason")
    if not isinstance(reason, str):
        reason = ""

    return {
        "intent": intent,
        "confidence": confidence,
        "reason": reason.strip(),
    }


async def _classify_route_intent_with_llm(
    llm: Any,
    state: CoordinatorAgentState,
    latest_text: str,
) -> dict[str, Any] | None:
    """调用 LLM 基于上下文判断应该分发到哪个智能体。"""

    context = _recent_conversation_context(state)
    response = await llm.ainvoke(
        [
            SystemMessage(content=ROUTE_DECISION_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "最近对话上下文：\n"
                    f"{context or '（无）'}\n\n"
                    f"当前用户输入：{latest_text or '（空）'}"
                )
            ),
        ]
    )
    return _parse_llm_route_decision(read_message_content(response))


def create_route_decision_node(llm: Any | None = None):
    """创建协调入口的意图路由节点。

    LLM 可用时优先用最近多轮上下文做二分类；LLM 不可用或返回异常时，
    再降级到较高置信度规则，避免入口协调器因为模型波动完全不可用。
    """

    @observe_node("coordinator.route_decision")
    async def route_decision_node(state: CoordinatorAgentState) -> CoordinatorAgentState:
        latest_text = _last_user_message(state)
        decision_source = "rule_fallback"
        route_reason = ""
        route_confidence: float | None = None
        route_intent = "route_planning" if _looks_like_route_request(latest_text) else "general_chat"

        if llm is not None:
            try:
                llm_decision = await _classify_route_intent_with_llm(llm, state, latest_text)
            except Exception:
                logger.warning("协调入口 LLM 意图识别失败，已降级为规则路由。", exc_info=True)
            else:
                if llm_decision is not None:
                    route_intent = str(llm_decision["intent"])
                    decision_source = "llm"
                    route_reason = str(llm_decision.get("reason") or "")
                    raw_confidence = llm_decision.get("confidence")
                    route_confidence = float(raw_confidence) if isinstance(raw_confidence, int | float) else None

        origin_text, destination_text, destination_city_hint, travel_mode = _extract_route_fields_from_context(state)
        metadata = dict(state.get("metadata", {}))
        metadata["route_decision"] = {
            "source": decision_source,
            "intent": route_intent,
            "reason": route_reason,
            "confidence": route_confidence,
        }
        return {
            "route_intent": route_intent,
            "target_agent_id": "route_planner_agent" if route_intent == "route_planning" else "chat_agent",
            "origin_text": origin_text,
            "destination_text": destination_text,
            "destination_city_hint": destination_city_hint,
            "travel_mode": travel_mode,
            "route_request_text": latest_text,
            "metadata": metadata,
        }

    return route_decision_node


def create_general_chat_node(llm: Any | None = None):
    """创建通用回复分支节点。"""

    chat_agent_node = create_chat_agent_node(llm)

    @observe_node("coordinator.general_chat")
    async def general_chat_node(state: CoordinatorAgentState) -> CoordinatorAgentState:
        result = await chat_agent_node(state)
        metadata = dict(state.get("metadata", {}))
        metadata["agent_id"] = "chat_agent"
        return {
            **result,
            "metadata": metadata,
        }

    return general_chat_node


def create_route_prepare_branch_node():
    """创建路线规划分支的预处理节点。"""

    validate_route_slots = create_validate_route_slots_node()

    @observe_node("coordinator.route_prepare_branch")
    async def route_prepare_branch_node(state: CoordinatorAgentState) -> CoordinatorAgentState:
        metadata = dict(state.get("metadata", {}))
        metadata["agent_id"] = "route_planner_agent"
        validated = await validate_route_slots(state)
        return {
            **validated,
            "metadata": metadata,
        }

    return route_prepare_branch_node


def create_route_prepare_human_interaction_node():
    """复用路线规划中的结构化补参准备逻辑。"""

    return create_prepare_human_interaction_node()


def create_route_resume_merge_node():
    """复用路线规划中的恢复合并逻辑。"""

    return create_resume_merge_node()


def create_route_execute_node(amap_route_toolset: AmapRouteToolset | None):
    """复用路线规划中的高德执行逻辑。"""

    return create_execute_route_plan_node(amap_route_toolset)


def create_route_finalize_node():
    """创建路线规划结果汇总节点。"""

    summarize_route_result = create_summarize_route_result_node()

    @observe_node("coordinator.route_finalize")
    async def route_finalize_node(state: CoordinatorAgentState) -> CoordinatorAgentState:
        result = await summarize_route_result(state)
        metadata = dict(result.get("metadata", {}))
        metadata["routed_by"] = "coordinator_agent"
        return {
            **result,
            "metadata": metadata,
        }

    return route_finalize_node


def create_passthrough_human_interaction_node():
    """复用共享的人机交互中断节点。"""

    return create_human_interaction_node()
