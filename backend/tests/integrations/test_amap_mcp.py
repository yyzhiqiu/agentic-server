"""高德 MCP 路线工具适配测试。"""

from __future__ import annotations

import pytest
from langchain_core.messages import ToolMessage

from app.integrations.amap_mcp import AmapRouteToolset, ResolvedLocation


class _FakeTool:
    """模拟 LangChain Tool 的最小异步调用接口。"""

    def __init__(self, name: str, result: object) -> None:
        self.name = name
        self.result = result
        self.calls: list[tuple[dict[str, object], dict[str, object]]] = []

    async def arun(self, args: dict[str, object], **kwargs: object) -> object:
        self.calls.append((dict(args), dict(kwargs)))
        return self.result

    async def ainvoke(self, args: dict[str, object], **kwargs: object) -> object:
        self.calls.append((dict(args), dict(kwargs)))
        return self.result


@pytest.mark.asyncio
async def test_amap_route_toolset_resolve_place_reads_toolmessage_artifact() -> None:
    geo_tool = _FakeTool(
        "maps_geo",
        ToolMessage(
            content="ok",
            tool_call_id="internal_maps_geo",
            artifact={
                "structured_content": {
                    "geocodes": [
                        {
                            "name": "深圳南山科技园",
                            "location": "113.93041,22.53332",
                            "city": "深圳",
                            "adcode": "440305",
                        }
                    ]
                }
            },
        ),
    )
    empty_tool = _FakeTool("unused_tool", ToolMessage(content="ok", tool_call_id="unused"))
    toolset = AmapRouteToolset(
        geo_tool=geo_tool,  # type: ignore[arg-type]
        text_search_tool=empty_tool,  # type: ignore[arg-type]
        driving_tool=empty_tool,  # type: ignore[arg-type]
        walking_tool=empty_tool,  # type: ignore[arg-type]
        transit_tool=empty_tool,  # type: ignore[arg-type]
    )

    location = await toolset.resolve_place("深圳南山科技园")

    assert location is not None
    assert location.name == "深圳南山科技园"
    assert location.location == "113.93041,22.53332"
    assert geo_tool.calls[0][1]["tool_call_id"] == "internal_maps_geo"


@pytest.mark.asyncio
async def test_amap_route_toolset_plan_route_reads_toolmessage_artifact() -> None:
    route_tool = _FakeTool(
        "maps_direction_driving",
        ToolMessage(
            content="ok",
            tool_call_id="internal_maps_direction_driving",
            artifact={
                "structured_content": {
                    "route": {
                        "paths": [
                            {
                                "distance": "1200",
                                "duration": "600",
                            }
                        ]
                    }
                }
            },
        ),
    )
    empty_tool = _FakeTool("unused_tool", ToolMessage(content="ok", tool_call_id="unused"))
    toolset = AmapRouteToolset(
        geo_tool=empty_tool,  # type: ignore[arg-type]
        text_search_tool=empty_tool,  # type: ignore[arg-type]
        driving_tool=route_tool,  # type: ignore[arg-type]
        walking_tool=empty_tool,  # type: ignore[arg-type]
        transit_tool=empty_tool,  # type: ignore[arg-type]
    )

    result = await toolset.plan_route(
        origin=ResolvedLocation(name="起点", location="113.1,22.1", city="深圳"),
        destination=ResolvedLocation(name="终点", location="113.2,22.2", city="深圳"),
        mode="driving",
    )

    assert result.mode == "driving"
    assert result.raw_route["route"]["paths"][0]["distance"] == "1200"
    assert route_tool.calls[0][1]["tool_call_id"] == "internal_maps_direction_driving"
