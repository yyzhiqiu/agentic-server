"""面向聊天请求的 LangGraph 执行适配器。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.common.exceptions import GraphException, LLMException
from app.graph.shared.messages import (
    chat_message_to_langchain_message,
    message_like_to_chat_message,
)
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ChatStreamEvent
from app.schemas.tool_call import ToolCallPayload


class GraphRunner:
    """基于预构建 LangGraph 实例执行聊天请求。"""

    def __init__(
        self,
        graph: Any,
        *,
        agent_id: str | None = None,
        llm_available: bool | None = None,
    ) -> None:
        self.graph = graph
        self.agent_id = agent_id or "unknown_agent"
        self.llm_available = llm_available

    @staticmethod
    def format_sse(event: str, payload: ChatStreamEvent | dict[str, Any]) -> str:
        """将结构化流式事件序列化为 SSE 数据块。"""

        body = payload.model_dump() if isinstance(payload, ChatStreamEvent) else payload
        return f"event: {event}\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"

    @staticmethod
    def _build_config(thread_id: str | None) -> dict[str, Any] | None:
        """把会话级 thread 标识映射为 LangGraph 的 ``thread_id`` 配置。"""

        if thread_id is None:
            return None
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _call_signature_mismatch(exc: TypeError) -> bool:
        """判断 ``TypeError`` 是否来自底层对象不接受新关键字参数。"""

        message = str(exc)
        return "unexpected keyword argument" in message or "positional argument" in message

    async def _invoke_with_fallbacks(
        self,
        func: Callable[..., Awaitable[Any]],
        payload: Any,
        *,
        thread_id: str | None = None,
    ) -> Any:
        """以兼容方式调用 LangGraph 异步方法。

        正常情况下会传入 ``config`` 与 ``durability``。若底层对象是测试替身，
        不接受这些关键字参数，则逐步降级重试，避免把兼容处理散落到测试代码中。
        """

        config = self._build_config(thread_id)
        attempts: list[dict[str, Any]] = []
        if config is not None:
            attempts.append({"config": config, "durability": "sync"})
            attempts.append({"config": config})
        attempts.append({})

        last_error: TypeError | None = None
        for kwargs in attempts:
            try:
                return await func(payload, **kwargs)
            except TypeError as exc:
                if not self._call_signature_mismatch(exc):
                    raise
                last_error = exc

        if last_error is not None:
            raise last_error
        return await func(payload)

    def _astream_events_with_fallbacks(
        self,
        payload: Any,
        *,
        thread_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """以兼容方式创建 LangGraph 事件流迭代器。"""

        astream_events = getattr(self.graph, "astream_events", None)
        if astream_events is None:
            raise AttributeError("graph does not provide astream_events")

        config = self._build_config(thread_id)
        attempts: list[dict[str, Any]] = []
        if config is not None:
            attempts.append({"config": config, "durability": "sync", "version": "v2"})
            attempts.append({"config": config, "version": "v2"})
        attempts.append({"version": "v2"})

        last_error: TypeError | None = None
        for kwargs in attempts:
            try:
                return astream_events(payload, **kwargs)
            except TypeError as exc:
                if not self._call_signature_mismatch(exc):
                    raise
                last_error = exc

        if last_error is not None:
            raise last_error
        return astream_events(payload, version="v2")

    def _build_state(self, request: ChatRequest, *, user_id: str | None = None) -> dict[str, Any]:
        """把聊天请求规整为图执行状态。

        这里优先读取显式 Schema 字段，再兼容旧版 ``metadata`` 扩展字段，
        让前端能够在切换到多 Agent 后直接使用稳定的请求契约。
        """

        metadata = dict(request.metadata)
        metadata.setdefault("agent_id", self.agent_id)
        state: dict[str, Any] = {
            "messages": [chat_message_to_langchain_message(message) for message in request.messages],
            "user_id": request.user_id or user_id,
            "conversation_id": request.conversation_id,
            "metadata": metadata,
        }

        for key in ("repository_context", "changed_files", "task_type"):
            if hasattr(request, key):
                value = getattr(request, key)
                if value is not None:
                    state[key] = value
                    continue
            if key in metadata:
                state[key] = metadata[key]
        return state

    @staticmethod
    def _messages_to_chat_messages(raw_messages: list[dict[str, Any]]) -> list[ChatMessage]:
        """把图状态中的消息数组转换为聊天消息 Schema。"""

        normalized: list[ChatMessage] = []
        for message in raw_messages:
            converted = message_like_to_chat_message(message)
            if converted is None or not converted.content:
                continue
            normalized.append(converted)
        return normalized

    @staticmethod
    def _assistant_message(messages: list[ChatMessage]) -> ChatMessage | None:
        """提取最后一条 assistant 消息。"""

        return next(
            (message for message in reversed(messages) if message.role == "assistant"),
            None,
        )

    @staticmethod
    def _json_object(value: Any) -> dict[str, Any]:
        """将任意图执行值规整为类 JSON 对象。"""

        if isinstance(value, dict):
            return dict(value)
        if value is None:
            return {}
        return {"value": value}

    @classmethod
    def _tool_call_from_raw(cls, raw_tool_call: dict[str, Any]) -> ToolCallPayload | None:
        """将原始图工具调用负载规整为响应 Schema。"""

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
    def _tool_calls_from_messages(cls, raw_messages: list[Any]) -> list[ToolCallPayload]:
        """从消息链路中提取工具调用结果。

        标准工具调用 graph 的执行轨迹通常保存在 ``messages`` 中，而不是顶层
        ``tool_calls`` 字段。这里会把模型发出的 ``tool_calls`` 与后续
        ``ToolMessage`` 对齐，规整为统一的响应 Schema。
        """

        tool_outputs_by_id: dict[str, ToolMessage] = {}
        for message in raw_messages:
            if isinstance(message, ToolMessage) and isinstance(message.tool_call_id, str):
                tool_outputs_by_id[message.tool_call_id] = message

        tool_calls: list[ToolCallPayload] = []
        for message in raw_messages:
            if not isinstance(message, AIMessage):
                continue

            for raw_tool_call in message.tool_calls:
                if not isinstance(raw_tool_call, dict):
                    continue

                normalized_call = dict(raw_tool_call)
                tool_call_id = normalized_call.get("id")
                output_message = (
                    tool_outputs_by_id.get(tool_call_id)
                    if isinstance(tool_call_id, str) and tool_call_id
                    else None
                )
                metadata = cls._json_object(normalized_call.get("metadata"))
                if isinstance(tool_call_id, str) and tool_call_id:
                    metadata.setdefault("tool_call_id", tool_call_id)
                if output_message is not None:
                    normalized_call.setdefault("status", output_message.status or "completed")
                    normalized_call.setdefault("output", output_message.content)
                    metadata.setdefault("tool_message_id", output_message.id)
                normalized_call["metadata"] = metadata

                normalized = cls._tool_call_from_raw(normalized_call)
                if normalized is not None:
                    tool_calls.append(normalized)

        return tool_calls

    @classmethod
    def _tool_calls_from_result(cls, result: dict[str, Any]) -> list[ToolCallPayload]:
        """从图执行结果负载中提取结构化工具调用。"""

        raw_tool_calls = result.get("tool_calls")
        if not isinstance(raw_tool_calls, list):
            metadata = result.get("metadata")
            if isinstance(metadata, dict):
                raw_tool_calls = metadata.get("tool_calls")

        if not isinstance(raw_tool_calls, list):
            raw_messages = result.get("messages")
            if isinstance(raw_messages, list):
                return cls._tool_calls_from_messages(raw_messages)
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
        """从 LangGraph 流事件中提取包含 messages 的状态片段。"""

        chunk = event.get("data", {}).get("chunk")
        if not isinstance(chunk, dict):
            return None
        if "messages" in chunk:
            return chunk
        for value in chunk.values():
            if isinstance(value, dict) and "messages" in value:
                return value
        return None

    def _response_from_result(self, result: dict[str, Any], request: ChatRequest) -> ChatResponse:
        """把图执行结果转换为标准聊天响应。"""

        raw_messages = result.get("messages", [])
        messages = self._messages_to_chat_messages(raw_messages)
        assistant_message = self._assistant_message(messages)
        if assistant_message is None:
            raise GraphException(
                "Agent Graph 执行失败",
                data={"error": "Graph result does not contain an assistant message"},
            )

        metadata = result.get("metadata")
        response_metadata = metadata if isinstance(metadata, dict) else {}
        agent_id = result.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            agent_id = response_metadata.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            agent_id = request.metadata.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            agent_id = self.agent_id

        return ChatResponse(
            conversation_id=result.get("conversation_id") or request.conversation_id,
            agent_id=agent_id,
            message=assistant_message,
            messages=messages,
            metadata={
                **response_metadata,
                "agent_id": agent_id,
            },
            tool_calls=self._tool_calls_from_result(result),
        )

    async def get_state(self, thread_id: str) -> Any | None:
        """读取指定运行在 checkpoint 中的最新图状态。"""

        aget_state = getattr(self.graph, "aget_state", None)
        if aget_state is None:
            return None

        config = self._build_config(thread_id)
        if config is None:
            return None

        try:
            return await aget_state(config)
        except TypeError as exc:
            if not self._call_signature_mismatch(exc):
                raise
            return await aget_state(config=config)

    async def update_state(
        self,
        thread_id: str,
        values: dict[str, Any],
        *,
        as_node: str | None = None,
    ) -> Any | None:
        """向指定 thread 的 checkpoint 状态写入一批预构造值。"""

        aupdate_state = getattr(self.graph, "aupdate_state", None)
        if aupdate_state is None:
            return None

        config = self._build_config(thread_id)
        if config is None:
            return None

        try:
            return await aupdate_state(config, values, as_node=as_node)
        except TypeError as exc:
            if not self._call_signature_mismatch(exc):
                raise
            return await aupdate_state(config=config, values=values, as_node=as_node)

    async def run_chat(
        self,
        request: ChatRequest,
        *,
        user_id: str | None = None,
        thread_id: str | None = None,
        resume: bool = False,
    ) -> ChatResponse:
        """为聊天请求执行一次非流式图调用。

        当 ``resume=True`` 时，会基于同一个 ``thread_id`` 从最近 checkpoint 恢复，
        不再重新构建初始输入状态。
        """

        if self.llm_available is False:
            raise LLMException(
                "LLM_API_KEY is not configured",
                data={"agent_id": self.agent_id},
            )

        try:
            state = None if resume else self._build_state(request, user_id=user_id)
            result = await self._invoke_with_fallbacks(
                self.graph.ainvoke,
                state,
                thread_id=thread_id,
            )
        except Exception as exc:
            raise GraphException(
                "Agent Graph 执行失败",
                data={"error": str(exc), "agent_id": self.agent_id},
            ) from exc

        return self._response_from_result(result, request)

    async def stream_chat_events(
        self,
        request: ChatRequest,
        *,
        user_id: str | None = None,
        thread_id: str | None = None,
        resume: bool = False,
    ) -> AsyncIterator[tuple[str, ChatStreamEvent]]:
        """为聊天请求持续产出结构化流式事件。"""

        yield ("start", ChatStreamEvent(type="start"))
        if self.llm_available is False:
            yield (
                "error",
                ChatStreamEvent(
                    type="error",
                    content="LLM_API_KEY is not configured",
                    data={
                        "code": LLMException().code.value,
                        "agent_id": self.agent_id,
                    },
                ),
            )
            return

        state = None if resume else self._build_state(request, user_id=user_id)
        last_content: str | None = None
        final_result: dict[str, Any] | None = None
        latest_state: dict[str, Any] | None = None
        try:
            try:
                iterator = self._astream_events_with_fallbacks(state, thread_id=thread_id)
            except AttributeError:
                response = await self.run_chat(
                    request,
                    user_id=user_id,
                    thread_id=thread_id,
                    resume=resume,
                )
                if response.message.content:
                    yield (
                        "message",
                        ChatStreamEvent(type="message", content=response.message.content),
                    )
                yield ("done", ChatStreamEvent(type="done", data=response.model_dump()))
                return

            async for event in iterator:
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

            response = self._response_from_result(final_result or latest_state or {}, request)
            if response.message.content and response.message.content != last_content:
                yield (
                    "message",
                    ChatStreamEvent(type="message", content=response.message.content),
                )
            yield ("done", ChatStreamEvent(type="done", data=response.model_dump()))
        except Exception as exc:
            error = exc if isinstance(exc, GraphException) else GraphException(
                "Agent Graph 执行失败",
                data={"error": str(exc), "agent_id": self.agent_id},
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
        self,
        request: ChatRequest,
        *,
        user_id: str | None = None,
        thread_id: str | None = None,
        resume: bool = False,
    ) -> AsyncIterator[str]:
        """将结构化图流事件序列化为 SSE 数据块。"""

        async for event, payload in self.stream_chat_events(
            request,
            user_id=user_id,
            thread_id=thread_id,
            resume=resume,
        ):
            yield self.format_sse(event, payload)
