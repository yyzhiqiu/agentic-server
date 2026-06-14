"""路线规划 Agent 的确定性节点实现。

本模块负责从用户输入抽取路线槽位、构建人机补参表单、调用高德能力执行
地点解析与路线规划，并把原始路线结果整理成适合聊天场景展示的摘要。

约束：
    - 路线规划流程按固定节点顺序执行，不让 LLM 自由选择工具。
    - 人机补参遵循共享 ``pending_human_input`` / ``resume`` 协议。
    - 高德返回结构存在多种层级与字段命名，摘要逻辑需要兼容变体。
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage

from app.common.exceptions import AppException
from app.graph.route_planner_agent.state import RoutePlannerAgentState
from app.graph.shared.messages import read_message_content, read_message_role
from app.integrations.amap_mcp import AmapRouteToolset, ResolvedLocation
from app.observability.decorators import observe_node

TRAVEL_MODE_LABELS = {
    "driving": "驾车",
    "walking": "步行",
    "transit": "公交",
}

AMBIGUOUS_DESTINATION_KEYWORDS = {
    "万象城",
    "软件园",
    "市政府",
    "火车站",
    "高铁站",
    "机场",
    "体育中心",
}

COMMON_CITY_OPTIONS = [
    {"label": "深圳", "value": "深圳"},
    {"label": "广州", "value": "广州"},
    {"label": "北京", "value": "北京"},
    {"label": "上海", "value": "上海"},
    {"label": "杭州", "value": "杭州"},
    {"label": "成都", "value": "成都"},
]


def _last_user_message(state: RoutePlannerAgentState) -> str:
    """提取当前状态中的最后一条用户消息。"""

    for message in reversed(state.get("messages", [])):
        if read_message_role(message) == "user":
            return read_message_content(message).strip()
    return ""


def _extract_route_fields(text: str) -> tuple[str | None, str | None, str | None]:
    """通过规则从路线请求中抽取起点、终点与出行方式。"""

    normalized = text.strip()
    if not normalized:
        return None, None, None

    travel_mode = None
    if any(keyword in normalized for keyword in ("公交", "地铁", "公共交通")):
        travel_mode = "transit"
    elif any(keyword in normalized for keyword in ("走路", "步行")):
        travel_mode = "walking"
    elif any(keyword in normalized for keyword in ("开车", "驾车", "自驾")):
        travel_mode = "driving"

    origin = None
    destination = None
    pair_match = re.search(r"从(?P<origin>.+?)到(?P<destination>.+?)(怎么去|怎么走|路线|导航|$)", normalized)
    if pair_match is not None:
        origin = pair_match.group("origin").strip(" ，,。")
        destination = pair_match.group("destination").strip(" ，,。")
        return origin or None, destination or None, travel_mode

    dest_match = re.search(r"(去|到)(?P<destination>.+?)(怎么去|怎么走|路线|导航|$)", normalized)
    if dest_match is not None:
        destination = dest_match.group("destination").strip(" ，,。")
    return origin, destination or None, travel_mode


def _missing_fields(state: RoutePlannerAgentState) -> list[str]:
    """根据当前状态计算仍需补充的必填字段。"""

    missing: list[str] = []
    if not state.get("origin_text"):
        missing.append("origin")
    if not state.get("destination_text"):
        missing.append("destination")
    if _needs_destination_city_hint(state):
        missing.append("destination_city_hint")
    if not state.get("travel_mode"):
        missing.append("travel_mode")
    return missing


def _needs_destination_city_hint(state: RoutePlannerAgentState) -> bool:
    """判断终点是否过于模糊，需要用户补充城市范围。"""

    destination_text = state.get("destination_text")
    if not isinstance(destination_text, str):
        return False

    normalized_destination = destination_text.strip()
    if not normalized_destination:
        return False
    if isinstance(state.get("destination_city_hint"), str) and state.get("destination_city_hint", "").strip():
        return False
    return normalized_destination in AMBIGUOUS_DESTINATION_KEYWORDS


def _normalize_validation_errors(state: RoutePlannerAgentState) -> dict[str, str]:
    """读取并规整当前状态中的字段校验错误。"""

    raw_errors = state.get("validation_errors")
    if not isinstance(raw_errors, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in raw_errors.items():
        if isinstance(key, str) and key and isinstance(value, str) and value.strip():
            normalized[key] = value.strip()
    return normalized


def _build_pending_human_input(state: RoutePlannerAgentState) -> dict[str, Any]:
    """根据缺失字段和校验错误构建结构化补参表单。

    Why:
        对路线规划来说，“有值”不等于“有效”。例如起点文本虽然存在，
        但高德地理解析失败时，前端仍然需要重新渲染该字段并展示错误原因，
        否则用户只会看到重复追问，却不知道究竟哪个字段需要修改。

    Returns:
        兼容共享人机交互协议的表单字典，供前端直接渲染。
    """

    missing_fields = list(state.get("missing_fields", []))
    validation_errors = _normalize_validation_errors(state)
    # 解析失败的字段即使当前已有值，也要重新加入表单，让用户明确知道需要澄清。
    for field_name in validation_errors:
        if field_name not in missing_fields:
            missing_fields.append(field_name)

    fields: list[dict[str, Any]] = []
    if "origin" in missing_fields:
        fields.append(
            {
                "name": "origin",
                "label": "起点",
                "type": "text",
                "required": True,
                "placeholder": "请输入出发地，例如：深圳南山科技园",
                "value": state.get("origin_text"),
            }
        )
    if "destination" in missing_fields:
        fields.append(
            {
                "name": "destination",
                "label": "终点",
                "type": "text",
                "required": True,
                "placeholder": "请输入目的地，例如：广州塔",
                "value": state.get("destination_text"),
            }
        )
    if "destination_city_hint" in missing_fields:
        fields.append(
            {
                "name": "destination_city_hint",
                "label": "终点所在城市",
                "type": "select",
                "required": True,
                "value": state.get("destination_city_hint"),
                "allow_custom": True,
                "custom_option_label": "其他城市",
                "custom_placeholder": "请输入终点所在城市，例如：苏州",
                "options": COMMON_CITY_OPTIONS,
            }
        )
    if "travel_mode" in missing_fields:
        fields.append(
            {
                "name": "travel_mode",
                "label": "出行方式",
                "type": "select",
                "required": True,
                "value": state.get("travel_mode"),
                "options": [
                    {"label": "驾车", "value": "driving"},
                    {"label": "步行", "value": "walking"},
                    {"label": "公交", "value": "transit"},
                ],
            }
        )

    label_map = {
        "origin": "起点",
        "destination": "终点",
        "destination_city_hint": "终点所在城市",
        "travel_mode": "出行方式",
    }
    readable_missing = "、".join(label_map[field] for field in missing_fields if field in label_map)
    error_messages = [validation_errors[field] for field in missing_fields if field in validation_errors]
    if error_messages:
        readable_errors = "；".join(error_messages)
        message = f"当前还需要补充或澄清 {readable_missing}。{readable_errors}"
    else:
        message = f"当前还缺少 {readable_missing}，请补充后继续路线规划。"
    return {
        "kind": "form",
        "title": "补充路线规划信息",
        "message": message,
        "fields": fields,
        "submit_label": "继续规划路线",
        "missing_fields": missing_fields,
    }


def _extract_resume_input_payload(state: RoutePlannerAgentState) -> dict[str, Any] | None:
    """提取恢复执行时的结构化补参输入。

    Why:
        新版人机交互节点会把表单值放到 ``human_input``，但历史运行记录与旧版
        恢复接口仍可能通过 ``metadata.resume_payload`` 传值。这里集中兼容两套
        协议，避免恢复逻辑散落在多个节点里。
    """

    human_input = state.get("human_input")
    if isinstance(human_input, dict):
        return human_input

    metadata = state.get("metadata", {})
    if not isinstance(metadata, dict):
        return None

    resume_payload = metadata.get("resume_payload", {})
    if not isinstance(resume_payload, dict):
        return None

    input_payload = resume_payload.get("input")
    if isinstance(input_payload, dict):
        return input_payload
    return None


def create_parse_route_request_node():
    """创建路线请求字段抽取节点。"""

    @observe_node("route_planner.parse_route_request")
    async def parse_route_request_node(state: RoutePlannerAgentState) -> RoutePlannerAgentState:
        """从最后一条用户消息中抽取路线槽位。

        Reads:
            messages: 当前轮次的对话消息。
            origin_text / destination_text / travel_mode: 历史已收集的槽位。

        Writes:
            route_request_text: 本轮用于解析的原始用户文本。
            origin_text / destination_text / travel_mode: 本轮抽取结果或已有值。
            destination_city_hint: 原样保留，等待后续节点判断是否需要补充。
            validation_errors: 继承已有字段错误，避免恢复执行时丢失提示。

        Notes:
            该节点只做轻量规则抽取，不调用外部地理服务。恢复执行时保留旧值，
            可以避免用户只补一个字段时把先前已确认的字段意外清空。
        """

        latest_text = _last_user_message(state)
        origin_text, destination_text, travel_mode = _extract_route_fields(latest_text)
        return {
            "route_request_text": latest_text,
            "origin_text": origin_text or state.get("origin_text"),
            "destination_text": destination_text or state.get("destination_text"),
            "destination_city_hint": state.get("destination_city_hint"),
            "travel_mode": travel_mode or state.get("travel_mode"),
            "validation_errors": _normalize_validation_errors(state),
        }

    return parse_route_request_node


def create_validate_route_slots_node():
    """创建路线规划必填字段校验节点。"""

    @observe_node("route_planner.validate_route_slots")
    async def validate_route_slots_node(state: RoutePlannerAgentState) -> RoutePlannerAgentState:
        """计算当前还缺哪些路线规划槽位。"""

        return {
            "missing_fields": _missing_fields(state),
            "validation_errors": _normalize_validation_errors(state),
        }

    return validate_route_slots_node


def create_prepare_human_interaction_node():
    """创建结构化补参准备节点。"""

    @observe_node("route_planner.prepare_human_interaction")
    async def prepare_human_interaction_node(state: RoutePlannerAgentState) -> RoutePlannerAgentState:
        """把缺失槽位转换成前端可直接渲染的表单。

        Reads:
            missing_fields: 当前尚未满足的必填字段。
            validation_errors: 字段解析失败或存在歧义时的错误说明。

        Writes:
            pending_human_input: 结构化表单协议。
            messages: 一条与表单文案保持一致的 assistant 提示消息。

        Notes:
            这里同时返回文本消息和结构化表单，是为了兼顾普通聊天展示与前端
            表单渲染，避免出现“界面有表单但消息历史里没有任何解释”的割裂感。
        """

        pending_human_input = _build_pending_human_input(state)
        return {
            "pending_human_input": pending_human_input,
            "messages": [
                AIMessage(content=pending_human_input["message"]),
            ],
            "validation_errors": _normalize_validation_errors(state),
        }

    return prepare_human_interaction_node


def create_resume_merge_node():
    """创建恢复后补参合并节点。"""

    @observe_node("route_planner.resume_merge")
    async def resume_merge_node(state: RoutePlannerAgentState) -> RoutePlannerAgentState:
        """合并用户补充的表单值，并清理一次性恢复载荷。

        Why:
            ``human_input`` 只代表当前这次恢复动作携带的输入，合并完成后必须
            立即清空，否则后续再次执行校验时会重复消费同一份表单数据，表现为
            “明明提交了却又弹回同一个表单”。
        """

        input_payload = _extract_resume_input_payload(state)
        if input_payload is None:
            return {
                "human_input": None,
                "pending_human_input": None,
                "missing_fields": _missing_fields(state),
                "validation_errors": _normalize_validation_errors(state),
            }

        origin_text = input_payload.get("origin")
        destination_text = input_payload.get("destination")
        destination_city_hint = input_payload.get("destination_city_hint")
        travel_mode = input_payload.get("travel_mode")
        # 先继承已确认的槽位，再按用户本次补参做覆盖，避免一次补参把其他字段冲掉。
        next_state: RoutePlannerAgentState = {
            "human_input": None,
            "pending_human_input": None,
            "origin_text": state.get("origin_text"),
            "destination_text": state.get("destination_text"),
            "destination_city_hint": state.get("destination_city_hint"),
            "travel_mode": state.get("travel_mode"),
            "validation_errors": {},
        }
        if isinstance(origin_text, str) and origin_text.strip():
            next_state["origin_text"] = origin_text.strip()
        if isinstance(destination_text, str) and destination_text.strip():
            next_state["destination_text"] = destination_text.strip()
        if isinstance(destination_city_hint, str) and destination_city_hint.strip():
            next_state["destination_city_hint"] = destination_city_hint.strip()
        if isinstance(travel_mode, str) and travel_mode in TRAVEL_MODE_LABELS:
            next_state["travel_mode"] = travel_mode
        next_state["missing_fields"] = _missing_fields(next_state)
        return next_state

    return resume_merge_node


def create_execute_route_plan_node(amap_route_toolset: AmapRouteToolset | None):
    """创建高德路线规划执行节点。"""

    @observe_node("route_planner.execute_route_plan")
    async def execute_route_plan_node(state: RoutePlannerAgentState) -> RoutePlannerAgentState:
        """执行地点解析与路线规划。

        Reads:
            origin_text / destination_text / destination_city_hint / travel_mode:
                已收集完成的路线槽位。

        Writes:
            resolved_origin / resolved_destination: 规范化后的地点信息。
            route_plan: 原始路线结果及出行方式。
            tool_calls: 可供响应、持久化和前端展示的标准工具调用轨迹。
            missing_fields / validation_errors: 当地点无法解析时，引导图重新进入补参。

        Side Effects:
            调用高德 MCP 进行地点解析与路线规划。

        Notes:
            起终点无法识别属于可恢复的用户输入问题，不应直接抛异常终止整个图；
            只有工具未配置或关键参数缺失这类系统问题，才返回硬错误。
        """

        if amap_route_toolset is None:
            raise AppException(
                message="当前环境未配置高德路线规划能力，请先在环境变量中配置 AMAP_MCP_KEY。",
                status_code=503,
            )

        origin_text = state.get("origin_text")
        destination_text = state.get("destination_text")
        travel_mode = state.get("travel_mode")
        if not origin_text or not destination_text or not travel_mode:
            raise AppException(
                message="路线规划参数不完整，无法继续执行。",
                status_code=409,
            )

        origin = await amap_route_toolset.resolve_place(origin_text)
        if origin is None:
            return {
                "pending_human_input": None,
                "missing_fields": ["origin"],
                "validation_errors": {
                    "origin": "暂时无法识别这个起点，请补充更具体的起点地址。",
                },
            }
        destination = await amap_route_toolset.resolve_place(destination_text)
        if destination is None:
            destination_city_hint = state.get("destination_city_hint")
            hint_text = (
                destination_city_hint.strip()
                if isinstance(destination_city_hint, str) and destination_city_hint.strip()
                else None
            )
            # 对高频重名地标优先让用户补城市，再带 city hint 进行二次解析。
            if hint_text is not None:
                destination = await amap_route_toolset.resolve_place(
                    destination_text,
                    city=hint_text,
                )
        if destination is None:
            return {
                "pending_human_input": None,
                "missing_fields": (
                    ["destination_city_hint", "destination"]
                    if _needs_destination_city_hint(state)
                    else ["destination"]
                ),
                "validation_errors": {
                    "destination": "暂时无法识别这个终点，请补充更具体的目的地。",
                    **(
                        {
                            "destination_city_hint": "这个终点名称可能存在重名，请补充终点所在城市后再试。"
                        }
                        if _needs_destination_city_hint(state)
                        else {}
                    ),
                },
            }

        route_result = await amap_route_toolset.plan_route(
            origin=origin,
            destination=destination,
            mode=travel_mode,
        )
        route_tool_names = {
            "driving": "maps_direction_driving",
            "walking": "maps_direction_walking",
            "transit": "maps_direction_transit_integrated",
        }
        return {
            "resolved_origin": _location_to_dict(route_result.origin),
            "resolved_destination": _location_to_dict(route_result.destination),
            "route_plan": {
                "mode": route_result.mode,
                "raw_route": route_result.raw_route,
            },
            "tool_calls": [
                {
                    "tool_name": route_tool_names.get(
                        route_result.mode,
                        "maps_direction",
                    ),
                    "status": "completed",
                    "input": {
                        "origin": origin.location,
                        "destination": destination.location,
                        "origin_text": origin_text,
                        "destination_text": destination_text,
                        "mode": route_result.mode,
                    },
                    "output": route_result.raw_route,
                    "metadata": {
                        "provider": "amap_mcp",
                        "agent_id": "route_planner_agent",
                    },
                }
            ],
            "missing_fields": [],
            "validation_errors": {},
        }

    return execute_route_plan_node


def _location_to_dict(location: ResolvedLocation) -> dict[str, Any]:
    """把解析后的地点信息转换为可持久化字典。"""

    return {
        "name": location.name,
        "location": location.location,
        "city": location.city,
        "adcode": location.adcode,
        "poi_id": location.poi_id,
    }


def _first_non_empty(*values: Any) -> Any | None:
    """返回首个非空值，用于兼容多种高德返回结构。"""

    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _route_containers(raw_route: dict[str, Any]) -> list[dict[str, Any]]:
    """按优先级返回可能包含路线详情的容器。"""

    containers: list[dict[str, Any]] = []
    route = raw_route.get("route")
    if isinstance(route, dict):
        containers.append(route)
    containers.append(raw_route)
    return containers


def _first_dict_item(value: Any) -> dict[str, Any] | None:
    """从列表字段中提取首个字典项。"""

    if not isinstance(value, list):
        return None
    for item in value:
        if isinstance(item, dict):
            return item
    return None


def _first_path(raw_route: dict[str, Any]) -> dict[str, Any] | None:
    """提取首条驾车或步行路线。"""

    for container in _route_containers(raw_route):
        first_path = _first_dict_item(container.get("paths"))
        if first_path is not None:
            return first_path
    return None


def _first_transit(raw_route: dict[str, Any]) -> dict[str, Any] | None:
    """提取首条公交换乘方案。"""

    for container in _route_containers(raw_route):
        first_transit = _first_dict_item(container.get("transits"))
        if first_transit is not None:
            return first_transit
    return None


def _to_float(value: Any) -> float | None:
    """把高德响应中的数字字段统一规整为浮点数。"""

    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    """把高德响应中的整数字段统一规整为整数。"""

    number = _to_float(value)
    if number is None:
        return None
    return int(round(number))


def _format_distance(value: Any) -> str | None:
    """把米制距离转换成更适合中文展示的格式。"""

    distance_meters = _to_float(value)
    if distance_meters is None:
        return None

    if distance_meters >= 1000:
        distance_km = distance_meters / 1000
        if distance_meters >= 100000 or distance_km.is_integer():
            return f"{distance_km:.0f} 公里"
        return f"{distance_km:.1f} 公里"
    return f"{int(round(distance_meters))} 米"


def _format_duration(value: Any) -> str | None:
    """把秒级时长转换成小时和分钟。"""

    duration_seconds = _to_int(value)
    if duration_seconds is None:
        return None
    if duration_seconds < 60:
        return "1 分钟内"

    total_minutes = max(1, int(round(duration_seconds / 60)))
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours} 小时 {minutes} 分钟"
    if hours:
        return f"{hours} 小时"
    return f"{minutes} 分钟"


def _format_cost(value: Any) -> str | None:
    """把费用字段格式化为元。"""

    amount = _to_float(value)
    if amount is None or amount <= 0:
        return None
    if amount.is_integer():
        return f"{amount:.0f} 元"
    return f"{amount:.1f} 元"


def _step_instructions_from_steps(steps: Any, *, limit: int = 3) -> list[str]:
    """从步骤数组中提取若干条可读指引，避免路线总结只展示第一步。"""

    if not isinstance(steps, list) or limit <= 0:
        return []

    instructions: list[str] = []
    seen: set[str] = set()
    for step in steps:
        if not isinstance(step, dict):
            continue
        instruction = step.get("instruction")
        if not isinstance(instruction, str):
            continue
        normalized = instruction.strip("。；; ")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        instructions.append(normalized)
        if len(instructions) >= limit:
            break
    return instructions


def _first_instruction_from_steps(steps: Any) -> str | None:
    """从步骤数组中提取首条可读指引。"""

    instructions = _step_instructions_from_steps(steps, limit=1)
    return instructions[0] if instructions else None


def _transit_busline_names(transit: dict[str, Any]) -> list[str]:
    """提取公交换乘方案中的线路名称，并保持原有顺序去重。"""

    names: list[str] = []
    seen: set[str] = set()
    segments = transit.get("segments")
    if not isinstance(segments, list):
        return names

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        bus = segment.get("bus")
        if not isinstance(bus, dict):
            continue
        buslines = bus.get("buslines")
        if not isinstance(buslines, list):
            continue
        for busline in buslines:
            if not isinstance(busline, dict):
                continue
            name = busline.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            normalized = name.strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            names.append(normalized)
    return names


def _first_transit_instruction(transit: dict[str, Any]) -> str | None:
    """提取公交方案中最适合作为首段提示的指引。"""

    segments = transit.get("segments")
    if not isinstance(segments, list):
        return None

    for segment in segments:
        if not isinstance(segment, dict):
            continue

        walking = segment.get("walking")
        if isinstance(walking, dict):
            instruction = _first_instruction_from_steps(walking.get("steps"))
            if instruction is not None:
                return instruction

        bus = segment.get("bus")
        if not isinstance(bus, dict):
            continue
        first_busline = _first_dict_item(bus.get("buslines"))
        if first_busline is None:
            continue
        line_name = first_busline.get("name")
        departure_stop = first_busline.get("departure_stop")
        departure_stop_name = (
            departure_stop.get("name")
            if isinstance(departure_stop, dict)
            else None
        )
        if isinstance(line_name, str) and line_name.strip():
            if isinstance(departure_stop_name, str) and departure_stop_name.strip():
                return f"前往 {departure_stop_name.strip()} 乘坐 {line_name.strip()}"
            return f"乘坐 {line_name.strip()}"
    return None


def _summarize_path_route(
    raw_route: dict[str, Any],
    *,
    mode: str | None,
) -> list[str]:
    """汇总驾车或步行路线的核心信息。"""

    first_path = _first_path(raw_route)
    if first_path is None:
        return []

    distance_text = _format_distance(first_path.get("distance"))
    duration_text = _format_duration(first_path.get("duration"))
    lines: list[str] = []

    overview_parts: list[str] = []
    if distance_text is not None:
        overview_parts.append(f"全程约 {distance_text}")
    if duration_text is not None:
        overview_parts.append(f"预计耗时 {duration_text}")
    if overview_parts:
        lines.append("，".join(overview_parts) + "。")

    detail_parts: list[str] = []
    tolls_text = _format_cost(first_path.get("tolls"))
    if tolls_text is not None:
        detail_parts.append(f"过路费约 {tolls_text}")
    traffic_lights = _to_int(first_path.get("traffic_lights"))
    if traffic_lights is not None and traffic_lights > 0:
        detail_parts.append(f"途经红绿灯约 {traffic_lights} 个")

    steps = first_path.get("steps")
    step_count = len([step for step in steps if isinstance(step, dict)]) if isinstance(steps, list) else 0
    if step_count > 0:
        step_label = "步行指引" if mode == "walking" else "导航指引"
        detail_parts.append(f"共 {step_count} 段{step_label}")
    if detail_parts:
        lines.append("，".join(detail_parts) + "。")

    step_previews = _step_instructions_from_steps(steps, limit=3)
    if step_previews:
        lines.append("路线预览：")
        for index, instruction in enumerate(step_previews, start=1):
            lines.append(f"{index}. {instruction}。")
        if step_count > len(step_previews):
            lines.append(f"……其余还有 {step_count - len(step_previews)} 段。")
    return lines


def _summarize_transit_route(raw_route: dict[str, Any]) -> list[str]:
    """汇总公交换乘方案的核心信息。"""

    first_transit = _first_transit(raw_route)
    if first_transit is None:
        distance_text = _format_distance(raw_route.get("distance"))
        if distance_text is None:
            return []
        return [
            f"起终点之间约 {distance_text}。",
            "当前没有返回可用的公交换乘明细，可尝试改用驾车或步行。",
        ]

    lines: list[str] = []
    overview_parts: list[str] = []

    distance_text = _format_distance(_first_non_empty(first_transit.get("distance"), raw_route.get("distance")))
    duration_text = _format_duration(_first_non_empty(first_transit.get("duration"), raw_route.get("duration")))
    walking_distance_text = _format_distance(first_transit.get("walking_distance"))
    if distance_text is not None:
        overview_parts.append(f"全程约 {distance_text}")
    if duration_text is not None:
        overview_parts.append(f"预计耗时 {duration_text}")
    if walking_distance_text is not None:
        overview_parts.append(f"步行约 {walking_distance_text}")
    if overview_parts:
        lines.append("，".join(overview_parts) + "。")

    busline_names = _transit_busline_names(first_transit)
    if busline_names:
        if len(busline_names) == 1:
            lines.append(f"推荐方案可直接乘坐 {busline_names[0]}。")
        else:
            preview = " -> ".join(busline_names[:3])
            if len(busline_names) > 3:
                preview = f"{preview} 等"
            lines.append(
                f"推荐方案包含 {len(busline_names)} 段公共交通，约需换乘 {len(busline_names) - 1} 次：{preview}。"
            )

    first_instruction = _first_transit_instruction(first_transit)
    if first_instruction is not None:
        lines.append(f"出发后可先 {first_instruction}。")
    segments = first_transit.get("segments")
    if isinstance(segments, list):
        transit_previews: list[str] = []
        seen_previews: set[str] = set()
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            walking = segment.get("walking")
            if isinstance(walking, dict):
                for instruction in _step_instructions_from_steps(walking.get("steps"), limit=1):
                    if instruction not in seen_previews:
                        seen_previews.add(instruction)
                        transit_previews.append(instruction)
                    if len(transit_previews) >= 3:
                        break
            if len(transit_previews) >= 3:
                break
        if transit_previews:
            lines.append("换乘预览：")
            for index, instruction in enumerate(transit_previews, start=1):
                lines.append(f"{index}. {instruction}。")
    return lines


def _summarize_route_result(state: RoutePlannerAgentState) -> str:
    """生成路线规划结果摘要文案。

    Why:
        高德返回的原始路线信息通常非常详细，但聊天首屏更适合展示“总览 +
        少量关键步骤”。更完整的结构化明细会继续保留在 ``metadata.route_plan``
        中，供地图 UI 或后续节点复用。
    """

    origin = state.get("resolved_origin") or {}
    destination = state.get("resolved_destination") or {}
    route_plan = state.get("route_plan") or {}
    mode = route_plan.get("mode")
    mode_label = TRAVEL_MODE_LABELS.get(mode, "规划")
    raw_route = route_plan.get("raw_route")

    origin_name = (
        origin.get("name")
        if isinstance(origin.get("name"), str) and origin.get("name")
        else state.get("origin_text") or "起点"
    )
    destination_name = (
        destination.get("name")
        if isinstance(destination.get("name"), str) and destination.get("name")
        else state.get("destination_text") or "终点"
    )

    summary_lines = [
        f"已为你生成从“{origin_name}”到“{destination_name}”的{mode_label}路线。",
    ]
    if isinstance(raw_route, dict):
        if mode == "transit":
            summary_lines.extend(_summarize_transit_route(raw_route))
        else:
            summary_lines.extend(_summarize_path_route(raw_route, mode=mode))
            if len(summary_lines) == 1:
                summary_lines.extend(_summarize_transit_route(raw_route))
    return "\n".join(summary_lines)


def create_summarize_route_result_node():
    """创建路线结果总结节点。"""

    @observe_node("route_planner.summarize_route_result")
    async def summarize_route_result_node(state: RoutePlannerAgentState) -> RoutePlannerAgentState:
        """把原始路线结果整理成最终聊天响应。

        Notes:
            一旦路线规划完成，需要清理掉中断态遗留的元数据，避免后端和前端把
            本轮已完成的运行误判为仍然处于待补参状态。
        """

        content = _summarize_route_result(state)
        route_plan = state.get("route_plan") or {}
        metadata = dict(state.get("metadata", {}))
        metadata["route_plan"] = {
            **route_plan,
            "origin": state.get("resolved_origin"),
            "destination": state.get("resolved_destination"),
        }
        # 完成态不应再保留人机中断痕迹，否则前端可能继续渲染历史表单。
        metadata.pop("pending_human_input", None)
        metadata.pop("resume_payload", None)
        metadata.pop("interrupt_source", None)
        metadata.pop("validation_errors", None)
        metadata["agent_id"] = "route_planner_agent"
        return {
            "metadata": metadata,
            "messages": [AIMessage(content=content)],
            "pending_human_input": None,
            "missing_fields": [],
            "validation_errors": {},
        }

    return summarize_route_result_node
