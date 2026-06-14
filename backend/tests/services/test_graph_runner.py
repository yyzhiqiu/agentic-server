"""图执行适配器的基础行为测试。"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from app.common.exceptions import LLMException
from app.graph.chat_agent.builder import build_chat_agent
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.graph_runner import GraphRunner


class _GraphWithToolCalls:
    async def ainvoke(self, state, **_: object):
        return {
            "conversation_id": state["conversation_id"],
            "messages": [
                *state["messages"],
                {"role": "assistant", "content": "Used search tool"},
            ],
            "tool_calls": [
                {
                    "tool_name": "search",
                    "status": "completed",
                    "input": {"query": "hello"},
                    "output": {"hits": 2},
                    "metadata": {"provider": "mock-tool"},
                }
            ],
            "metadata": {"model": "mock"},
        }


class _GraphCapturingConfig:
    def __init__(self) -> None:
        self.received_state = None
        self.received_kwargs: dict[str, object] = {}

    async def ainvoke(self, state, **kwargs: object):
        self.received_state = state
        self.received_kwargs = kwargs
        return {
            "conversation_id": "conversation-1",
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "ok"},
            ],
            "metadata": {"model": "mock"},
        }


class _GraphCapturingResume:
    def __init__(self) -> None:
        self.received_state = None
        self.received_kwargs: dict[str, object] = {}

    async def ainvoke(self, state, **kwargs: object):
        self.received_state = state
        self.received_kwargs = kwargs
        return {
            "conversation_id": "conversation-1",
            "messages": [
                {"role": "assistant", "content": "已恢复执行"},
            ],
            "metadata": {"agent_id": "route_planner_agent"},
        }


class _GraphWithInterrupt:
    async def ainvoke(self, state, **_: object):
        prompt = {
            "kind": "form",
            "title": "补充路线规划信息",
            "message": "当前还缺少起点，请补充后继续路线规划。",
            "fields": [
                {
                    "name": "origin",
                    "label": "起点",
                    "type": "text",
                    "required": True,
                    "placeholder": "请输入起点",
                }
            ],
            "submit_label": "继续规划路线",
            "missing_fields": ["origin"],
        }
        return {
            "conversation_id": state.get("conversation_id"),
            "messages": [
                {"role": "assistant", "content": prompt["message"]},
            ],
            "__interrupt__": (prompt,),
            "metadata": {"agent_id": "route_planner_agent"},
        }


class _GraphWithMessageToolCalls:
    async def ainvoke(self, state, **_: object):
        return {
            "conversation_id": state["conversation_id"],
            "messages": [
                *state["messages"],
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_time",
                            "args": {"query": "now"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content="2026-06-08 00:00:00",
                    tool_call_id="call_1",
                    status="success",
                ),
                AIMessage(content="现在时间是 2026-06-08 00:00:00"),
            ],
            "metadata": {"model": "mock"},
        }


class _GraphWithJsonToolOutput:
    async def ainvoke(self, state, **_: object):
        return {
            "conversation_id": state["conversation_id"],
            "messages": [
                *state["messages"],
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search",
                            "args": {"query": "OpenAI"},
                            "id": "call_json",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content='{"query":"OpenAI","results":[{"title":"OpenAI"}]}',
                    tool_call_id="call_json",
                    status="success",
                ),
                AIMessage(content="已找到 OpenAI"),
            ],
            "metadata": {"model": "mock"},
        }


class _GraphWithHistoricalToolCalls:
    async def ainvoke(self, state, **_: object):
        return {
            "conversation_id": state["conversation_id"],
            "messages": [
                HumanMessage(content="old question"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search",
                            "args": {"query": "old"},
                            "id": "call_old",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content='{"results":["old"]}',
                    tool_call_id="call_old",
                    status="success",
                ),
                AIMessage(content="old answer"),
                HumanMessage(content="new question"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_time",
                            "args": {},
                            "id": "call_new",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content="2026-06-14 23:33:14",
                    tool_call_id="call_new",
                    status="success",
                ),
                AIMessage(content="new answer"),
            ],
            "metadata": {"model": "mock"},
        }


class _GraphStreamingInterrupt:
    async def aget_state(self, config, **_: object):
        _ = config
        prompt = {
            "kind": "form",
            "title": "补充路线规划信息",
            "message": "当前还缺少起点、出行方式，请补充后继续路线规划。",
            "fields": [
                {
                    "name": "origin",
                    "label": "起点",
                    "type": "text",
                    "required": True,
                    "placeholder": "请输入起点",
                },
                {
                    "name": "travel_mode",
                    "label": "出行方式",
                    "type": "select",
                    "required": True,
                    "options": [
                        {"label": "驾车", "value": "driving"},
                        {"label": "步行", "value": "walking"},
                        {"label": "公交", "value": "transit"},
                    ],
                },
            ],
            "submit_label": "继续规划路线",
            "missing_fields": ["origin", "travel_mode"],
        }
        return {
            "values": {
                "conversation_id": "conversation-1",
                "metadata": {"agent_id": "route_planner_agent"},
                "messages": [
                    HumanMessage(content="我要去广东"),
                    AIMessage(content=prompt["message"]),
                ],
                "__interrupt__": (prompt,),
            }
        }

    async def astream_events(self, state, **_: object):
        _ = state
        prompt = {
            "kind": "form",
            "title": "补充路线规划信息",
            "message": "当前还缺少起点、出行方式，请补充后继续路线规划。",
            "fields": [
                {
                    "name": "origin",
                    "label": "起点",
                    "type": "text",
                    "required": True,
                    "placeholder": "请输入起点",
                },
                {
                    "name": "travel_mode",
                    "label": "出行方式",
                    "type": "select",
                    "required": True,
                    "options": [
                        {"label": "驾车", "value": "driving"},
                        {"label": "步行", "value": "walking"},
                        {"label": "公交", "value": "transit"},
                    ],
                },
            ],
            "submit_label": "继续规划路线",
            "missing_fields": ["origin", "travel_mode"],
        }
        yield {
            "event": "on_chain_stream",
            "data": {
                "chunk": {
                    "messages": [
                        {"role": "assistant", "content": prompt["message"]},
                    ],
                    "__interrupt__": (prompt,),
                }
            },
        }


class _GraphStreamingModelAndToolEvents:
    async def astream_events(self, state, **_: object):
        _ = state
        yield {
            "event": "on_chat_model_stream",
            "run_id": "route-model",
            "metadata": {"langgraph_node": "route_decision"},
            "data": {"chunk": AIMessage(content='{"intent":"general_chat"}')},
        }
        yield {
            "event": "on_chain_start",
            "run_id": "model-node",
            "tags": ["graph:step:2"],
            "metadata": {"langgraph_node": "model"},
            "data": {},
        }
        yield {
            "event": "on_chat_model_start",
            "run_id": "answer-model",
            "metadata": {"langgraph_node": "model"},
            "data": {},
        }
        for content in ("你", "好"):
            yield {
                "event": "on_chat_model_stream",
                "run_id": "answer-model",
                "metadata": {"langgraph_node": "model"},
                "data": {"chunk": AIMessage(content=content)},
            }
        yield {
            "event": "on_tool_start",
            "name": "get_time",
            "run_id": "tool-run",
            "metadata": {"langgraph_node": "tools"},
            "data": {"input": {}},
        }
        yield {
            "event": "on_tool_end",
            "name": "get_time",
            "run_id": "tool-run",
            "metadata": {"langgraph_node": "tools"},
            "data": {
                "input": {},
                "output": ToolMessage(
                    content="2026-06-14 23:00:00",
                    name="get_time",
                    tool_call_id="call-1",
                ),
            },
        }
        yield {
            "event": "on_chain_end",
            "run_id": "model-node",
            "tags": ["graph:step:2"],
            "metadata": {"langgraph_node": "model"},
            "data": {},
        }
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "run_id": "graph-run",
            "tags": [],
            "metadata": {},
            "data": {
                "output": {
                    "messages": [
                        HumanMessage(content="hello"),
                        AIMessage(content="你好"),
                    ],
                    "metadata": {"agent_id": "chat_agent"},
                }
            },
        }


@pytest.mark.asyncio
async def test_graph_runner_streams_token_node_and_tool_events() -> None:
    runner = GraphRunner(
        _GraphStreamingModelAndToolEvents(),
        agent_id="coordinator_agent",
    )
    request = ChatRequest(messages=[ChatMessage(role="user", content="hello")])

    events = [event async for event in runner.stream_chat_events(request)]

    message_events = [
        payload for event_name, payload in events if event_name == "message"
    ]
    assert [event.content for event in message_events] == ["你", "好"]
    assert all("intent" not in (event.content or "") for event in message_events)

    node_events = [
        (event_name, payload.data["node"])
        for event_name, payload in events
        if event_name in {"node_start", "node_end"}
    ]
    assert node_events == [("node_start", "model"), ("node_end", "model")]

    tool_start = next(payload for name, payload in events if name == "tool_start")
    tool_end = next(payload for name, payload in events if name == "tool_end")
    assert tool_start.data["tool_name"] == "get_time"
    assert tool_end.data["status"] == "completed"
    assert tool_end.data["output"]["role"] == "tool"
    assert tool_end.data["output"]["content"] == "2026-06-14 23:00:00"


@pytest.mark.asyncio
async def test_graph_runner_returns_mock_response() -> None:
    runner = GraphRunner(build_chat_agent(llm=None), agent_id="chat_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    response = await runner.run_chat(request)

    assert response.conversation_id == "conversation-1"
    assert response.message.role == "assistant"
    assert "Mock response" in response.message.content


@pytest.mark.asyncio
async def test_graph_runner_extracts_tool_calls_from_graph_result() -> None:
    runner = GraphRunner(_GraphWithToolCalls())
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    response = await runner.run_chat(request)

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "search"
    assert response.tool_calls[0].output == {"hits": 2}


@pytest.mark.asyncio
async def test_graph_runner_extracts_tool_calls_from_message_chain() -> None:
    runner = GraphRunner(_GraphWithMessageToolCalls())
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    response = await runner.run_chat(request)

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "get_time"
    assert response.tool_calls[0].status == "success"
    assert response.tool_calls[0].input == {"query": "now"}
    assert response.tool_calls[0].output == {"value": "2026-06-08 00:00:00"}
    assert response.tool_calls[0].metadata["tool_call_id"] == "call_1"


@pytest.mark.asyncio
async def test_graph_runner_parses_json_object_tool_output() -> None:
    runner = GraphRunner(_GraphWithJsonToolOutput())
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="search")],
    )

    response = await runner.run_chat(request)

    assert response.tool_calls[0].output == {
        "query": "OpenAI",
        "results": [{"title": "OpenAI"}],
    }


@pytest.mark.asyncio
async def test_graph_runner_only_extracts_current_turn_tool_calls() -> None:
    runner = GraphRunner(_GraphWithHistoricalToolCalls())
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="new question")],
    )

    response = await runner.run_chat(request)

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "get_time"
    assert response.tool_calls[0].metadata["tool_call_id"] == "call_new"


@pytest.mark.asyncio
async def test_graph_runner_raises_when_llm_is_marked_unavailable() -> None:
    runner = GraphRunner(
        build_chat_agent(llm=None),
        agent_id="chat_agent",
        llm_available=False,
    )
    request = ChatRequest(messages=[ChatMessage(role="user", content="hello")])

    with pytest.raises(LLMException):
        await runner.run_chat(request)


@pytest.mark.asyncio
async def test_graph_runner_passes_thread_id_to_langgraph_config() -> None:
    graph = _GraphCapturingConfig()
    runner = GraphRunner(graph, agent_id="chat_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    await runner.run_chat(request, thread_id="conversation-1")

    assert graph.received_kwargs["config"] == {
        "configurable": {
            "thread_id": "conversation-1",
        }
    }
    assert graph.received_kwargs["durability"] == "sync"
    assert isinstance(graph.received_state["messages"][0], HumanMessage)


@pytest.mark.asyncio
async def test_graph_runner_resume_uses_none_as_input_state() -> None:
    graph = _GraphCapturingConfig()
    runner = GraphRunner(graph, agent_id="chat_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="hello")],
    )

    await runner.run_chat(request, thread_id="conversation-1", resume=True)

    assert graph.received_state is None


@pytest.mark.asyncio
async def test_graph_runner_resume_uses_command_payload_when_input_is_present() -> None:
    graph = _GraphCapturingResume()
    runner = GraphRunner(graph, agent_id="route_planner_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="我要去广东")],
        metadata={"resume_payload": {"input": {"origin": "深圳", "travel_mode": "driving"}}},
    )

    await runner.run_chat(request, thread_id="conversation-1", resume=True)

    assert isinstance(graph.received_state, Command)
    assert graph.received_state.resume == {"origin": "深圳", "travel_mode": "driving"}


@pytest.mark.asyncio
async def test_graph_runner_maps_interrupt_to_pending_human_input() -> None:
    runner = GraphRunner(_GraphWithInterrupt(), agent_id="route_planner_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="我要去广东")],
    )

    response = await runner.run_chat(request)

    assert response.agent_id == "route_planner_agent"
    assert response.pending_human_input is not None
    assert response.pending_human_input.title == "补充路线规划信息"
    assert response.pending_human_input.missing_fields == ["origin"]
    assert response.metadata["interrupt_source"] == "human_input"
    assert response.metadata["resume_available"] is True


@pytest.mark.asyncio
async def test_graph_runner_stream_returns_full_history_and_interrupt_payload() -> None:
    runner = GraphRunner(_GraphStreamingInterrupt(), agent_id="route_planner_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="我要去广东")],
    )

    events = [event async for event in runner.stream_chat_events(request, thread_id="conversation-1")]

    interrupt_event = next(payload for name, payload in events if name == "interrupt")
    done_event = next(payload for name, payload in events if name == "done")

    assert interrupt_event.data["pending_human_input"]["missing_fields"] == [
        "origin",
        "travel_mode",
    ]
    assert len(done_event.data["messages"]) == 2
    assert done_event.data["messages"][0]["role"] == "user"
    assert done_event.data["messages"][0]["content"] == "我要去广东"
    assert done_event.data["messages"][1]["role"] == "assistant"
    assert done_event.data["pending_human_input"]["missing_fields"] == [
        "origin",
        "travel_mode",
    ]


@pytest.mark.asyncio
async def test_graph_runner_preserves_custom_select_field_metadata() -> None:
    class _GraphWithCustomSelectInterrupt:
        async def ainvoke(self, state, **_: object):
            prompt = {
                "kind": "form",
                "title": "补充偏好信息",
                "message": "请选择偏好，或填写自定义选项。",
                "fields": [
                    {
                        "name": "preference",
                        "label": "偏好",
                        "type": "select",
                        "required": True,
                        "allow_custom": True,
                        "custom_option_label": "其他偏好",
                        "custom_placeholder": "请输入你的偏好",
                        "options": [
                            {"label": "高铁", "value": "rail"},
                            {"label": "飞机", "value": "flight"},
                        ],
                    }
                ],
                "submit_label": "继续",
                "missing_fields": ["preference"],
            }
            return {
                "conversation_id": state.get("conversation_id"),
                "messages": [
                    {"role": "assistant", "content": prompt["message"]},
                ],
                "__interrupt__": (prompt,),
                "metadata": {"agent_id": "route_planner_agent"},
            }

    runner = GraphRunner(_GraphWithCustomSelectInterrupt(), agent_id="route_planner_agent")
    request = ChatRequest(
        conversation_id="conversation-1",
        messages=[ChatMessage(role="user", content="帮我选个偏好")],
    )

    response = await runner.run_chat(request)

    assert response.pending_human_input is not None
    field = response.pending_human_input.fields[0]
    assert field.allow_custom is True
    assert field.custom_option_label == "其他偏好"
    assert field.custom_placeholder == "请输入你的偏好"
