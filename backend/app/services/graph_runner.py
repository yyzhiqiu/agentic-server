"""面向聊天请求的 LangGraph 执行适配器。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command, GraphOutput

from app.common.exceptions import GraphException, LLMException
from app.graph.shared.human_input import normalize_pending_human_input
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
    def _build_resume_command(request: ChatRequest) -> Command | None:
        """从恢复请求里提取可传给 LangGraph 的 resume 命令。"""

        resume_payload = request.metadata.get("resume_payload")
        if not isinstance(resume_payload, dict):
            return None
        input_payload = resume_payload.get("input")
        if input_payload is None:
            return None
        return Command(resume=input_payload)

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

    @staticmethod
    def _event_node(event: dict[str, Any]) -> str | None:
        """读取 LangGraph 事件所属节点。"""

        metadata = event.get("metadata")
        if not isinstance(metadata, dict):
            return None
        node = metadata.get("langgraph_node")
        return node if isinstance(node, str) and node else None

    @staticmethod
    def _event_run_id(event: dict[str, Any]) -> str | None:
        """读取 LangChain 事件运行标识，用作流式消息边界。"""

        run_id = event.get("run_id")
        return str(run_id) if run_id is not None else None

    @staticmethod
    def _is_graph_step(event: dict[str, Any]) -> bool:
        """判断链事件是否对应一个实际图节点，而非内部 Runnable。"""

        tags = event.get("tags")
        return isinstance(tags, list) and any(
            isinstance(tag, str) and tag.startswith("graph:step:")
            for tag in tags
        )

    @staticmethod
    def _should_stream_model_event(event: dict[str, Any]) -> bool:
        """过滤仅供内部决策使用的模型输出。

        协调器的 ``route_decision`` 会输出结构化 JSON，它属于控制面数据，
        不应作为聊天正文暴露给用户。其他模型调用均保留独立消息边界，
        包括工具调用前的说明和工具完成后的最终答复。
        """

        return GraphRunner._event_node(event) != "route_decision"

    @staticmethod
    def _message_chunk_text(chunk: Any) -> str:
        """从模型流式消息块中提取纯文本增量。"""

        content = getattr(chunk, "content", None)
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return ""

        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    @classmethod
    def _stream_json_value(cls, value: Any) -> Any:
        """把工具事件负载转换为 SSE 可序列化结构。"""

        if isinstance(value, dict):
            return {
                str(key): cls._stream_json_value(item)
                for key, item in value.items()
            }
        if isinstance(value, tuple | list):
            return [cls._stream_json_value(item) for item in value]
        if isinstance(value, str | int | float | bool) or value is None:
            return value

        converted = message_like_to_chat_message(value)
        if converted is not None:
            return converted.model_dump()
        return str(value)

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
        """将任意图执行值规整为类 JSON 对象。

        工具消息常把结构化结果序列化成 JSON 字符串。对象形式的 JSON 会在这里
        还原，避免数据库出现 ``{"value": "{\"results\": ...}"}`` 的二次编码。
        """

        if isinstance(value, dict):
            return dict(value)
        if value is None:
            return {}
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed
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
        ``ToolMessage`` 对齐，规整为统一的响应 Schema。图结果可能携带完整 thread
        历史，因此只读取最后一条用户消息之后的当前轮消息，避免旧工具调用被重复
        归入新运行。
        """

        last_human_index = next(
            (
                index
                for index in range(len(raw_messages) - 1, -1, -1)
                if isinstance(raw_messages[index], HumanMessage)
            ),
            0,
        )
        current_turn_messages = raw_messages[last_human_index:]
        tool_outputs_by_id: dict[str, ToolMessage] = {}
        for message in current_turn_messages:
            if isinstance(message, ToolMessage) and isinstance(message.tool_call_id, str):
                tool_outputs_by_id[message.tool_call_id] = message

        tool_calls: list[ToolCallPayload] = []
        for message in current_turn_messages:
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

    @staticmethod
    def _extract_interrupt_chunk(event: dict[str, Any]) -> list[Any]:
        """从 LangGraph 流事件中提取中断负载。"""

        chunk = event.get("data", {}).get("chunk")
        if not isinstance(chunk, dict):
            return []
        interrupts = chunk.get("__interrupt__")
        if not isinstance(interrupts, tuple | list):
            return []
        return list(interrupts)

    @staticmethod
    def _result_value(result: dict[str, Any] | GraphOutput) -> dict[str, Any]:
        """兼容 GraphOutput 与旧版 dict 结果。"""

        if isinstance(result, GraphOutput):
            value = result.value
            if isinstance(value, dict):
                return dict(value)
            return {"value": value}
        return dict(result)

    @staticmethod
    def _result_interrupts(result: dict[str, Any] | GraphOutput) -> list[Any]:
        """兼容 GraphOutput 与旧版 dict 结果中的中断信息。"""

        if isinstance(result, GraphOutput):
            return list(result.interrupts)
        interrupts = result.get("__interrupt__")
        if isinstance(interrupts, tuple | list):
            return list(interrupts)
        return []

    @staticmethod
    def _snapshot_values(snapshot: Any | None) -> dict[str, Any]:
        """从不同形态的 checkpoint 快照中提取 ``values`` 负载。"""

        if snapshot is None:
            return {}

        values = getattr(snapshot, "values", None)
        if isinstance(values, dict):
            return dict(values)

        if isinstance(snapshot, dict):
            raw_values = snapshot.get("values")
            if isinstance(raw_values, dict):
                return dict(raw_values)
            return dict(snapshot)

        return {}

    @classmethod
    def _message_count(cls, candidate: dict[str, Any] | GraphOutput | None) -> int:
        """统计候选结果里原始消息数组的长度，用于选择更完整的状态。"""

        if candidate is None:
            return 0

        normalized = cls._result_value(candidate) if isinstance(candidate, GraphOutput) else dict(candidate)
        raw_messages = normalized.get("messages")
        return len(raw_messages) if isinstance(raw_messages, list) else 0

    @classmethod
    def _merge_result_with_snapshot(
        cls,
        result: dict[str, Any] | GraphOutput | None,
        snapshot: Any | None,
    ) -> dict[str, Any]:
        """用 checkpoint 快照补全图结果，优先保留消息更完整的一侧。"""

        normalized_result = cls._result_value(result) if result is not None else {}
        snapshot_values = cls._snapshot_values(snapshot)
        if not snapshot_values:
            return normalized_result

        merged = dict(snapshot_values)
        merged.update(normalized_result)

        if cls._message_count(snapshot_values) >= cls._message_count(normalized_result):
            snapshot_messages = snapshot_values.get("messages")
            if isinstance(snapshot_messages, list):
                merged["messages"] = snapshot_messages

        return merged

    @staticmethod
    def _attach_interrupt_result(
        result: dict[str, Any],
        interrupt_payload: Any | None,
    ) -> dict[str, Any]:
        """把流式阶段捕获到的中断负载回填到最终结果中。"""

        if interrupt_payload is None:
            return result

        enriched = dict(result)
        enriched["__interrupt__"] = (interrupt_payload,)
        return enriched

    def _append_interrupt_metadata(
        self,
        response: ChatResponse,
        interrupts: list[Any],
    ) -> ChatResponse:
        """把 LangGraph 中断结果映射为响应中的待补参协议。"""

        if not interrupts:
            return response

        pending_human_input = normalize_pending_human_input(interrupts[0])
        if pending_human_input is None:
            return response

        metadata = dict(response.metadata)
        metadata["agent_id"] = response.agent_id or self.agent_id
        metadata["interrupt_source"] = "human_input"
        metadata["pending_human_input"] = pending_human_input.model_dump()
        metadata["resume_available"] = True
        return response.model_copy(
            update={
                "metadata": metadata,
                "pending_human_input": pending_human_input,
            }
        )

    def _response_from_result(
        self,
        result: dict[str, Any] | GraphOutput,
        request: ChatRequest,
    ) -> ChatResponse:
        """把图执行结果转换为标准聊天响应。"""

        normalized_result = self._result_value(result)
        raw_messages = normalized_result.get("messages", [])
        messages = self._messages_to_chat_messages(raw_messages)
        assistant_message = self._assistant_message(messages)
        if assistant_message is None:
            raise GraphException(
                "Agent Graph 执行失败",
                data={"error": "Graph result does not contain an assistant message"},
            )

        metadata = normalized_result.get("metadata")
        response_metadata = metadata if isinstance(metadata, dict) else {}
        agent_id = normalized_result.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            agent_id = response_metadata.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            agent_id = request.metadata.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            agent_id = self.agent_id

        response = ChatResponse(
            conversation_id=normalized_result.get("conversation_id") or request.conversation_id,
            agent_id=agent_id,
            message=assistant_message,
            messages=messages,
            metadata={
                **response_metadata,
                "agent_id": agent_id,
            },
            tool_calls=self._tool_calls_from_result(normalized_result),
        )
        return self._append_interrupt_metadata(
            response,
            self._result_interrupts(result),
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
            state: Any
            if resume:
                state = self._build_resume_command(request)
            else:
                state = self._build_state(request, user_id=user_id)
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

        snapshot = await self.get_state(thread_id) if thread_id is not None else None
        normalized_result = self._merge_result_with_snapshot(result, snapshot)
        interrupts = self._result_interrupts(result)
        normalized_result = self._attach_interrupt_result(
            normalized_result,
            interrupts[0] if interrupts else None,
        )
        return self._response_from_result(normalized_result, request)

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

        last_streamed_content = ""
        active_message_id: str | None = None
        final_result: dict[str, Any] | None = None
        latest_state: dict[str, Any] | None = None
        interrupt_payload: dict[str, Any] | None = None
        interrupt_result: Any | None = None
        try:
            try:
                iterator_input = (
                    self._build_resume_command(request)
                    if resume
                    else self._build_state(request, user_id=user_id)
                )
                iterator = self._astream_events_with_fallbacks(
                    iterator_input,
                    thread_id=thread_id,
                )
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
                event_type = event.get("event")
                event_node = self._event_node(event)

                if (
                    event_type == "on_chain_start"
                    and event_node is not None
                    and self._is_graph_step(event)
                ):
                    yield (
                        "node_start",
                        ChatStreamEvent(
                            type="node_start",
                            data={
                                "node": event_node,
                                "event_id": self._event_run_id(event),
                            },
                        ),
                    )
                    continue

                if (
                    event_type == "on_chain_end"
                    and event_node is not None
                    and self._is_graph_step(event)
                ):
                    yield (
                        "node_end",
                        ChatStreamEvent(
                            type="node_end",
                            data={
                                "node": event_node,
                                "event_id": self._event_run_id(event),
                            },
                        ),
                    )
                    continue

                if event_type == "on_chat_model_start" and self._should_stream_model_event(event):
                    active_message_id = self._event_run_id(event)
                    last_streamed_content = ""
                    continue

                if event_type == "on_chat_model_stream" and self._should_stream_model_event(event):
                    chunk = event.get("data", {}).get("chunk")
                    delta = self._message_chunk_text(chunk)
                    if not delta:
                        continue
                    message_id = self._event_run_id(event) or active_message_id
                    last_streamed_content += delta
                    yield (
                        "message",
                        ChatStreamEvent(
                            type="message",
                            content=delta,
                            data={
                                "delta": True,
                                "message_id": message_id,
                                "node": event_node,
                            },
                        ),
                    )
                    continue

                if event_type == "on_tool_start":
                    yield (
                        "tool_start",
                        ChatStreamEvent(
                            type="tool_start",
                            data={
                                "tool_name": event.get("name"),
                                "tool_call_id": self._event_run_id(event),
                                "input": self._stream_json_value(
                                    event.get("data", {}).get("input")
                                ),
                                "node": event_node,
                            },
                        ),
                    )
                    continue

                if event_type == "on_tool_end":
                    event_data = event.get("data", {})
                    yield (
                        "tool_end",
                        ChatStreamEvent(
                            type="tool_end",
                            data={
                                "tool_name": event.get("name"),
                                "tool_call_id": self._event_run_id(event),
                                "input": self._stream_json_value(event_data.get("input")),
                                "output": self._stream_json_value(event_data.get("output")),
                                "status": "completed",
                                "node": event_node,
                            },
                        ),
                    )
                    continue

                if event.get("event") == "on_chain_stream":
                    latest_state = self._extract_state_chunk(event) or latest_state
                    interrupts = self._extract_interrupt_chunk(event)
                    if interrupts and interrupt_payload is None:
                        interrupt_result = interrupts[0]
                        pending_human_input = normalize_pending_human_input(interrupts[0])
                        if pending_human_input is not None:
                            interrupt_payload = pending_human_input.model_dump()
                    continue

                if event.get("event") == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict):
                        final_result = output

            snapshot = await self.get_state(thread_id) if thread_id is not None else None
            response_result = self._merge_result_with_snapshot(
                final_result or latest_state or {},
                snapshot,
            )
            response_result = self._attach_interrupt_result(
                response_result,
                interrupt_result,
            )
            response = self._response_from_result(response_result, request)
            if response.message.content and response.message.content != last_streamed_content:
                yield (
                    "message",
                    ChatStreamEvent(
                        type="message",
                        content=response.message.content,
                        data={
                            "delta": False,
                            "replace": True,
                            "message_id": response.message.metadata.get("message_id"),
                            "node": response.agent_id,
                        },
                    ),
                )
            if interrupt_payload is not None:
                yield (
                    "interrupt",
                    ChatStreamEvent(
                        type="interrupt",
                        content=response.message.content,
                        data={
                            "pending_human_input": interrupt_payload,
                            "agent_id": response.agent_id or self.agent_id,
                            "conversation_id": response.conversation_id,
                        },
                    ),
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
