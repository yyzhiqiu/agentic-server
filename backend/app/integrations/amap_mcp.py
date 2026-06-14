"""高德 MCP 路线规划工具集成。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.common.exceptions import AppException
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ResolvedLocation:
    """描述已解析的地点信息。"""

    name: str
    location: str
    city: str | None = None
    adcode: str | None = None
    poi_id: str | None = None


@dataclass(slots=True)
class AmapRouteResult:
    """描述结构化路线规划结果。"""

    origin: ResolvedLocation
    destination: ResolvedLocation
    mode: str
    raw_route: dict[str, Any]


@dataclass(slots=True)
class AmapRouteToolset:
    """封装路线规划实际所需的高德 MCP 工具。"""

    geo_tool: BaseTool
    text_search_tool: BaseTool
    driving_tool: BaseTool
    walking_tool: BaseTool
    transit_tool: BaseTool

    @staticmethod
    def _first_item(raw: Any, *keys: str) -> dict[str, Any] | None:
        """从高德工具输出里取出第一个候选结果。"""

        if not isinstance(raw, dict):
            return None

        for key in keys:
            value = raw.get(key)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return dict(value[0])
        return None

    @staticmethod
    def _location_from_payload(
        item: dict[str, Any],
        *,
        fallback_name: str,
    ) -> ResolvedLocation | None:
        """把高德地点解析或搜索结果规整为内部地点结构。"""

        location = item.get("location")
        if not isinstance(location, str) or not location:
            return None

        city = item.get("city")
        if not isinstance(city, str) or not city:
            city = item.get("cityname")
        normalized_city = city if isinstance(city, str) and city else None

        adcode = item.get("adcode")
        normalized_adcode = adcode if isinstance(adcode, str) and adcode else None

        poi_id = item.get("id")
        if not isinstance(poi_id, str) or not poi_id:
            poi_id = item.get("poi_id")
        normalized_poi_id = poi_id if isinstance(poi_id, str) and poi_id else None

        name = item.get("name")
        if not isinstance(name, str) or not name:
            name = item.get("formatted_address")
        if not isinstance(name, str) or not name:
            name = item.get("address")
        normalized_name = name if isinstance(name, str) and name else fallback_name

        return ResolvedLocation(
            name=normalized_name,
            location=location,
            city=normalized_city,
            adcode=normalized_adcode,
            poi_id=normalized_poi_id,
        )

    @staticmethod
    def _content_text_candidates(content: Any) -> list[str]:
        """从工具 content 片段中提取可能的 JSON 文本。"""

        if isinstance(content, str):
            return [content]
        if not isinstance(content, list):
            return []

        texts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                texts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text)
        return texts

    @classmethod
    def _payload_from_content(cls, content: Any) -> dict[str, Any]:
        """兼容从 ToolMessage.content 的 JSON 文本中读取结构化负载。"""

        for text in cls._content_text_candidates(content):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return {}

    @classmethod
    def _structured_payload(
        cls,
        *,
        content: Any,
        artifact: dict[str, Any],
    ) -> dict[str, Any]:
        """统一解析 artifact 与 content 中的结构化负载。

        Why:
            高德 MCP 在不同工具与适配器版本下，可能把可用数据放在
            ``artifact.structured_content``，也可能只放在 ``ToolMessage.content`` 的 JSON
            文本中。这里集中兼容，避免把正常地点误判成“无法识别”。
        """

        structured_content = artifact.get("structured_content")
        if isinstance(structured_content, dict):
            return dict(structured_content)

        if any(key in artifact for key in ("results", "geocodes", "pois", "route")):
            return dict(artifact)

        return cls._payload_from_content(content)

    @staticmethod
    async def _invoke_tool(tool: BaseTool, args: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """统一兼容 LangChain Tool 在直调场景下的返回形态。

        Why:
            MCP 适配器把工具声明为 ``response_format="content_and_artifact"``，但直接调
            ``tool.arun()`` 时返回值并不稳定，这里统一补齐解析入口。
        """

        tool_name = getattr(tool, "name", "mcp_tool")
        result = await tool.arun(
            args,
            tool_call_id=f"internal_{tool_name}",
        )
        if isinstance(result, tuple) and len(result) == 2:
            content, artifact = result
        elif isinstance(result, ToolMessage):
            content = result.content
            artifact = result.artifact
        else:
            content = result
            artifact = None

        return content, artifact if isinstance(artifact, dict) else {}

    async def resolve_place(
        self,
        text: str,
        *,
        city: str | None = None,
    ) -> ResolvedLocation | None:
        """解析用户输入的地点文本。"""

        normalized_text = text.strip()
        if not normalized_text:
            return None

        geo_args: dict[str, Any] = {"address": normalized_text}
        if city:
            geo_args["city"] = city

        try:
            geo_content, geo_artifact = await self._invoke_tool(self.geo_tool, geo_args)
        except Exception:
            logger.info("高德地点解析失败，将回退到地点搜索继续尝试。", exc_info=True)
        else:
            geo_payload = self._structured_payload(
                content=geo_content,
                artifact=geo_artifact,
            )
            geo_item = self._first_item(geo_payload, "geocodes", "results", "pois")
            location = self._location_from_payload(
                geo_item or {},
                fallback_name=normalized_text,
            )
            if location is not None:
                return location

        search_args: dict[str, Any] = {"keywords": normalized_text}
        if city:
            search_args["city"] = city
            search_args["citylimit"] = True

        try:
            search_content, search_artifact = await self._invoke_tool(
                self.text_search_tool,
                search_args,
            )
        except Exception:
            logger.warning("高德地点搜索失败，无法继续解析地点。", exc_info=True)
            return None

        search_payload = self._structured_payload(
            content=search_content,
            artifact=search_artifact,
        )
        search_item = self._first_item(search_payload, "pois", "results", "geocodes")
        return self._location_from_payload(
            search_item or {},
            fallback_name=normalized_text,
        )

    async def plan_route(
        self,
        *,
        origin: ResolvedLocation,
        destination: ResolvedLocation,
        mode: str,
    ) -> AmapRouteResult:
        """按指定交通方式调用高德路线规划工具。"""

        if mode == "driving":
            route_content, route_artifact = await self._invoke_tool(
                self.driving_tool,
                {
                    "origin": origin.location,
                    "destination": destination.location,
                },
            )
        elif mode == "walking":
            route_content, route_artifact = await self._invoke_tool(
                self.walking_tool,
                {
                    "origin": origin.location,
                    "destination": destination.location,
                },
            )
        elif mode == "transit":
            if not origin.city or not destination.city:
                raise AppException(
                    message="公交路线规划缺少起点或终点城市信息，请补充更具体的地点。",
                    status_code=409,
                )
            route_content, route_artifact = await self._invoke_tool(
                self.transit_tool,
                {
                    "origin": origin.location,
                    "destination": destination.location,
                    "city": origin.city,
                    "cityd": destination.city,
                },
            )
        else:
            raise AppException(
                message="暂不支持当前出行方式。",
                status_code=400,
                data={"mode": mode},
            )

        raw_route = self._structured_payload(
            content=route_content,
            artifact=route_artifact,
        )
        return AmapRouteResult(
            origin=origin,
            destination=destination,
            mode=mode,
            raw_route=raw_route if isinstance(raw_route, dict) else {},
        )


def build_amap_mcp_url() -> str | None:
    """根据环境变量拼装高德 MCP 的访问地址。"""

    base_url = settings.AMAP_MCP_BASE_URL
    if not base_url or not settings.AMAP_MCP_KEY:
        return None
    return f"{base_url}?{urlencode({'key': settings.AMAP_MCP_KEY})}"


async def create_amap_route_toolset() -> AmapRouteToolset | None:
    """在启动阶段创建高德 MCP 路线工具集。"""

    url = build_amap_mcp_url()
    if url is None:
        logger.info("未配置 AMAP_MCP_KEY，将跳过高德 MCP 初始化。")
        return None

    client = MultiServerMCPClient(
        {
            "amap": {
                "transport": "streamable_http",
                "url": url,
                "timeout": timedelta(seconds=settings.AMAP_MCP_TIMEOUT_SECONDS),
                "sse_read_timeout": timedelta(seconds=settings.AMAP_MCP_TIMEOUT_SECONDS),
            }
        }
    )
    try:
        tools = await client.get_tools(server_name="amap")
    except Exception:
        logger.warning("初始化高德 MCP 工具失败，将以降级模式继续启动。", exc_info=True)
        return None

    tool_map = {tool.name: tool for tool in tools}
    required_tools = {
        "maps_geo": "geo_tool",
        "maps_text_search": "text_search_tool",
        "maps_direction_driving": "driving_tool",
        "maps_direction_walking": "walking_tool",
        "maps_direction_transit_integrated": "transit_tool",
    }
    missing = [tool_name for tool_name in required_tools if tool_name not in tool_map]
    if missing:
        logger.warning("高德 MCP 缺少必要工具：%s", ",".join(missing))
        return None

    return AmapRouteToolset(
        geo_tool=tool_map["maps_geo"],
        text_search_tool=tool_map["maps_text_search"],
        driving_tool=tool_map["maps_direction_driving"],
        walking_tool=tool_map["maps_direction_walking"],
        transit_tool=tool_map["maps_direction_transit_integrated"],
    )
