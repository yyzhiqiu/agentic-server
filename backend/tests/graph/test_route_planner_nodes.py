from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from app.graph.route_planner_agent.nodes import (
    _summarize_route_result,
    create_parse_route_request_node,
    create_prepare_human_interaction_node,
    create_resume_merge_node,
    create_validate_route_slots_node,
)
from app.graph.shared.nodes.human_interaction import create_human_interaction_node


@pytest.mark.asyncio
async def test_route_planner_asks_for_city_hint_when_destination_is_ambiguous() -> None:
    parse_node = create_parse_route_request_node()
    validate_node = create_validate_route_slots_node()
    prepare_node = create_prepare_human_interaction_node()
    state = {
        "messages": [HumanMessage(content="我要去万象城")],
        "metadata": {},
    }

    state = {**state, **(await parse_node(state))}
    state = {**state, **(await validate_node(state))}
    result = await prepare_node(state)

    pending_human_input = result["pending_human_input"]
    assert pending_human_input is not None
    field_names = [field["name"] for field in pending_human_input["fields"]]
    assert "destination_city_hint" in field_names

    city_hint_field = next(
        field for field in pending_human_input["fields"] if field["name"] == "destination_city_hint"
    )
    assert city_hint_field["type"] == "select"
    assert city_hint_field["allow_custom"] is True
    assert city_hint_field["custom_option_label"] == "其他城市"
    assert city_hint_field["custom_placeholder"] == "请输入终点所在城市，例如：苏州"


@pytest.mark.asyncio
async def test_route_planner_resume_merge_accepts_custom_city_hint() -> None:
    resume_merge_node = create_resume_merge_node()
    state = {
        "origin_text": "深圳湾万象城",
        "destination_text": "万象城",
        "metadata": {
            "resume_payload": {
                "input": {
                    "destination_city_hint": "苏州",
                    "travel_mode": "driving",
                }
            }
        },
    }

    result = await resume_merge_node(state)

    assert result["destination_city_hint"] == "苏州"
    assert result["travel_mode"] == "driving"
    assert "destination_city_hint" not in result["missing_fields"]


@pytest.mark.asyncio
async def test_human_interaction_node_returns_resume_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node = create_human_interaction_node()

    def fake_interrupt(_: dict[str, object]) -> dict[str, str]:
        return {
            "origin": "深圳南山科技园",
            "travel_mode": "driving",
        }

    monkeypatch.setattr(
        "app.graph.shared.nodes.human_interaction.interrupt",
        fake_interrupt,
    )

    result = await node(
        {
            "pending_human_input": {
                "kind": "form",
                "title": "补充路线规划信息",
            }
        }
    )

    assert result["human_input"] == {
        "origin": "深圳南山科技园",
        "travel_mode": "driving",
    }
    assert result["pending_human_input"] is None


@pytest.mark.asyncio
async def test_route_planner_resume_merge_prefers_human_input_payload() -> None:
    resume_merge_node = create_resume_merge_node()
    state = {
        "destination_text": "万象城",
        "metadata": {
            "resume_payload": {
                "input": {
                    "origin": "旧起点",
                    "travel_mode": "walking",
                }
            }
        },
        "human_input": {
            "origin": "深圳南山科技园",
            "destination_city_hint": "深圳",
            "travel_mode": "driving",
        },
    }

    result = await resume_merge_node(state)

    assert result["origin_text"] == "深圳南山科技园"
    assert result["destination_city_hint"] == "深圳"
    assert result["travel_mode"] == "driving"
    assert result["human_input"] is None


@pytest.mark.asyncio
async def test_route_planner_latest_request_overrides_checkpoint_destination() -> None:
    parse_node = create_parse_route_request_node()

    result = await parse_node(
        {
            "origin_text": "南京",
            "destination_text": "北京",
            "travel_mode": "driving",
            "messages": [HumanMessage(content="我要去西安")],
            "metadata": {},
        }
    )

    assert result["origin_text"] == "南京"
    assert result["destination_text"] == "西安"
    assert result["travel_mode"] == "driving"


def test_summarize_route_result_supports_top_level_driving_paths() -> None:
    summary = _summarize_route_result(
        {
            "resolved_origin": {"name": "南京"},
            "resolved_destination": {"name": "西安"},
            "route_plan": {
                "mode": "driving",
                "raw_route": {
                    "origin": "118.796877,32.060255",
                    "destination": "108.93977,34.341574",
                    "paths": [
                        {
                            "distance": "1086844",
                            "duration": "39786",
                            "steps": [
                                {"instruction": "向西行驶49米左转"},
                                {"instruction": "沿北京东路向西行驶147米左转"},
                            ],
                        }
                    ],
                },
            },
        }
    )

    assert "已为你生成从“南京”到“西安”的驾车路线。" in summary
    assert "全程约 1087 公里" in summary
    assert "预计耗时 11 小时 3 分钟" in summary
    assert "共 2 段导航指引" in summary
    assert "路线预览：" in summary
    assert "1. 向西行驶49米左转。" in summary
    assert "2. 沿北京东路向西行驶147米左转。" in summary


def test_summarize_route_result_supports_walking_route_paths() -> None:
    summary = _summarize_route_result(
        {
            "resolved_origin": {"name": "南京市政府"},
            "resolved_destination": {"name": "玄武湖"},
            "route_plan": {
                "mode": "walking",
                "raw_route": {
                    "route": {
                        "paths": [
                            {
                                "distance": 282,
                                "duration": 226,
                                "steps": [
                                    {"instruction": "向东南步行52米向左后方行走"},
                                    {"instruction": "向北步行125米右转"},
                                ],
                            }
                        ]
                    }
                },
            },
        }
    )

    assert "已为你生成从“南京市政府”到“玄武湖”的步行路线。" in summary
    assert "全程约 282 米" in summary
    assert "预计耗时 4 分钟" in summary
    assert "共 2 段步行指引" in summary
    assert "路线预览：" in summary
    assert "1. 向东南步行52米向左后方行走。" in summary
    assert "2. 向北步行125米右转。" in summary


def test_summarize_route_result_supports_top_level_transits() -> None:
    summary = _summarize_route_result(
        {
            "resolved_origin": {"name": "南京"},
            "resolved_destination": {"name": "新街口"},
            "route_plan": {
                "mode": "transit",
                "raw_route": {
                    "distance": "2837",
                    "transits": [
                        {
                            "duration": "1511",
                            "walking_distance": "1204",
                            "segments": [
                                {
                                    "walking": {
                                        "steps": [
                                            {"instruction": "步行52米向右前方行走"},
                                        ]
                                    },
                                    "bus": {
                                        "buslines": [
                                            {
                                                "name": "地铁3号线(林场--秣陵)",
                                                "departure_stop": {"name": "鸡鸣寺"},
                                            }
                                        ]
                                    },
                                }
                            ],
                        }
                    ],
                },
            },
        }
    )

    assert "已为你生成从“南京”到“新街口”的公交路线。" in summary
    assert "全程约 2.8 公里" in summary
    assert "预计耗时 25 分钟" in summary
    assert "步行约 1.2 公里" in summary
    assert "推荐方案可直接乘坐 地铁3号线(林场--秣陵)。" in summary
    assert "出发后可先 步行52米向右前方行走。" in summary


def test_summarize_route_result_falls_back_when_details_missing() -> None:
    summary = _summarize_route_result(
        {
            "origin_text": "南京",
            "destination_text": "西安",
            "route_plan": {
                "mode": "driving",
                "raw_route": {},
            },
        }
    )

    assert summary == "已为你生成从“南京”到“西安”的驾车路线。"
