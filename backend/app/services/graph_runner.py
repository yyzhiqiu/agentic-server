"""面向聊天请求的图执行适配器。

本模块封装预先构建好的 LangGraph 实例，并将图执行结果转换为聊天 Schema
和流式事件。它不负责持久化或 HTTP 响应编排，这些职责保留在 Service
层与 API 层中。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from app.common.exceptions import GraphException, LLMException
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ChatStreamEvent
from app.schemas.tool_call import ToolCallPayload

class GraphRunner:
    """基于预构建 LangGraph 实例执行聊天请求。"""

    def __init__(self, graph: Any, *, llm_available: bool = True) -> None:
        self.graph = graph
        self.llm_available = llm_available

    @staticmethod
    def format_sse(event: str, payload: ChatStreamEvent | dict[str, Any]) -> str:
        """将结构化流式事件序列化为一个 SSE 数据块。"""

        body = payload.model_dump() if isinstance(payload, ChatStreamEvent) else payload
        return f"event: {event}\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"

    @staticmethod
    def _build_state(request: ChatRequest, *, user_id: str | None = None) -> dict[str, Any]:
        return {
            "messages": [message.model_dump() for message in request.messages],
            "user_id": request.user_id or user_id,
            "conversation_id": request.conversation_id,
            "metadata": request.metadata,
        }

    @staticmethod
    def _messages_to_chat_messages(raw_messages: list[dict[str, Any]]) -> list[ChatMessage]:
        return [
            ChatMessage(
                role=message.get("role", "assistant"),
                content=str(message.get("content", "")),
                metadata=message.get("metadata", {}),
            )
            for message in raw_messages
            if message.get("content")
        ]

    @staticmethod
    def _assistant_message(messages: list[ChatMessage]) -> ChatMessage | None:
        return next(
            (message for message in reversed(messages) if message.role == "assistant"),
            None,
        )

    @staticmethod
    def _json_object(value: Any) -> dict[str, Any]:
        """将任意图执行值规范化为类 JSON 对象。"""

        if isinstance(value, dict):
            return dict(value)
        if value is None:
            return {}
        return {"value": value}

    @classmethod
    def _tool_call_from_raw(cls, raw_tool_call: dict[str, Any]) -> ToolCallPayload | None:
        """将原始图工具调用负载规范化为响应 Schema。"""

        tool_name = raw_tool_call.get("tool_name") or raw_tool_call.get("name")
        if not isinstance(tool_name, str) or not tool_name:
            return None

        status = raw_tool_call.get("status")
        if not isinstance(status, str) or not status:
            status = "completed"

        return ToolCallPayload(
            tool_name=tool_name,
            status=status,
            input=cls._json_object(raw_tool_call.get("input", raw_tool_call.get("args"))),
            output=cls._json_object(raw_tool_call.get("output", raw_tool_call.get("result"))),
            metadata=cls._json_object(raw_tool_call.get("metadata")),
        )

    @classmethod
    def _tool_calls_from_result(cls, result: dict[str, Any]) -> list[ToolCallPayload]:
        """从图执行结果负载中提取结构化工具调用。"""

        raw_tool_calls = result.get("tool_calls")
        if not isinstance(raw_tool_calls, list):
            metadata = result.get("metadata")
            if isinstance(metadata, dict):
                raw_tool_calls = metadata.get("tool_calls")

        if not isinstance(raw_tool_calls, list):
            return []

        tool_calls: list[ToolCallPayload] = []
        for item in raw_tool_calls:
            if not isinstance(item, dict):
                continue
            normalized = cls._tool_call_from_raw(item)
            if normalized is not None:
                tool_calls.append(normalized)
        return tool_calls

    @staticmethod
    def _extract_state_chunk(event: dict[str, Any]) -> dict[str, Any] | None:
        chunk = event.get("data", {}).get("chunk")
        if not isinstance(chunk, dict):
            return None
        if "messages" in chunk:
            return chunk
        for value in chunk.values():
            if isinstance(value, dict) and "messages" in value:
                return value
        return None

    @classmethod
    def _response_from_result(
        cls, result: dict[str, Any], request: ChatRequest
    ) -> ChatResponse:
        raw_messages = result.get("messages", [])
        messages = cls._messages_to_chat_messages(raw_messages)
        assistant_message = cls._assistant_message(messages)
        if assistant_message is None:
            raise GraphException(
                "Agent Graph 执行失败",
                data={"error": "Graph result does not contain an assistant message"},
            )
        return ChatResponse(
            conversation_id=result.get("conversation_id") or request.conversation_id,
            message=assistant_message,
            messages=messages,
            metadata=result.get("metadata", {}),
            tool_calls=cls._tool_calls_from_result(result),
        )

    async def run_chat(self, request: ChatRequest, *, user_id: str | None = None) -> ChatResponse:
        """为聊天请求执行一次非流式图调用。"""

        if not self.llm_available:
            raise LLMException("LLM_API_KEY is not configured", data={"provider": "mock-disabled"})
        try:
            state = self._build_state(request, user_id=user_id)
            result = await self.graph.ainvoke(state)
        except Exception as exc:
            raise GraphException("Agent Graph 执行失败", data={"error": str(exc)}) from exc

        return self._response_from_result(result, request)

    async def stream_chat_events(
        self, request: ChatRequest, *, user_id: str | None = None
    ) -> AsyncIterator[tuple[str, ChatStreamEvent]]:
        """为聊天请求持续产出结构化流式事件。"""

        if not self.llm_available:
            error = LLMException("LLM_API_KEY is not configured", data={"provider": "mock-disabled"})
            yield (
                "error",
                ChatStreamEvent(
                    type="error",
                    content=error.message,
                    data={
                        **error.data,
                        "code": error.code.value,
                    },
                ),
            )
            return
        yield ("start", ChatStreamEvent(type="start"))
        state = self._build_state(request, user_id=user_id)
        last_content: str | None = None
        final_result: dict[str, Any] | None = None
        latest_state: dict[str, Any] | None = None
        try:
            astream_events = getattr(self.graph, "astream_events", None)
            if astream_events is None:
                response = await self.run_chat(request, user_id=user_id)
                if response.message.content:
                    yield (
                        "message",
                        ChatStreamEvent(type="message", content=response.message.content),
                    )
                yield ("done", ChatStreamEvent(type="done", data=response.model_dump()))
                return

            async for event in astream_events(state, version="v2"):
                if event.get("event") == "on_chain_stream":
                    latest_state = self._extract_state_chunk(event) or latest_state
                    if latest_state is None:
                        continue
                    messages = self._messages_to_chat_messages(latest_state.get("messages", []))
                    assistant_message = self._assistant_message(messages)
                    if (
                        assistant_message is not None
                        and assistant_message.content
                        and assistant_message.content != last_content
                    ):
                        last_content = assistant_message.content
                        yield (
                            "message",
                            ChatStreamEvent(type="message", content=assistant_message.content),
                        )

                if event.get("event") == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict):
                        final_result = output

            response = self._response_from_result(final_result or latest_state or state, request)
            if response.message.content and response.message.content != last_content:
                yield (
                    "message",
                    ChatStreamEvent(type="message", content=response.message.content),
                )
            yield ("done", ChatStreamEvent(type="done", data=response.model_dump()))
        except Exception as exc:
            error = exc if isinstance(exc, GraphException) else GraphException(
                "Agent Graph 执行失败",
                data={"error": str(exc)},
            )
            yield (
                "error",
                ChatStreamEvent(
                    type="error",
                    content=error.message,
                    data={
                        **error.data,
                        "code": error.code.value,
                    },
                ),
            )

    async def stream_chat(
        self, request: ChatRequest, *, user_id: str | None = None
    ) -> AsyncIterator[str]:
        """将结构化图流式事件序列化为 SSE 数据块。"""

        async for event, payload in self.stream_chat_events(request, user_id=user_id):
            yield self.format_sse(event, payload)
