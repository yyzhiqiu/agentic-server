"""LangGraph 消息类型适配工具。

本模块负责在项目自定义的聊天 Schema、LangChain 消息对象以及测试中常见的
字典消息结构之间做双向转换，避免消息格式处理逻辑散落在 GraphRunner、
Graph Node 和 Service 层中。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.schemas.chat import ChatMessage


def message_content_to_text(content: Any) -> str:
    """把不同消息内容结构规整为纯文本。"""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
                    continue
            parts.append(str(item))
        return "\n".join(part for part in parts if part)

    if content is None:
        return ""
    return str(content)


def read_message_role(message: Any) -> str | None:
    """读取消息对象对应的标准聊天角色。"""

    if isinstance(message, BaseMessage):
        message_type = getattr(message, "type", "")
        if message_type == "human":
            return "user"
        if message_type == "ai":
            return "assistant"
        if message_type in {"system", "tool"}:
            return message_type
        if message_type == "chat":
            role = getattr(message, "role", None)
            return str(role) if isinstance(role, str) and role else "assistant"
        return None

    if isinstance(message, dict):
        role = message.get("role")
        if isinstance(role, str) and role:
            return role

        message_type = message.get("type")
        if message_type == "human":
            return "user"
        if message_type == "ai":
            return "assistant"
        if message_type in {"system", "tool"}:
            return str(message_type)

    return None


def read_message_content(message: Any) -> str:
    """读取消息对象中的文本内容。"""

    if isinstance(message, BaseMessage):
        return message_content_to_text(message.content)

    if isinstance(message, dict):
        return message_content_to_text(message.get("content"))

    return message_content_to_text(message)


def read_message_name(message: Any) -> str | None:
    """读取消息对象中的 name 字段。"""

    if isinstance(message, BaseMessage):
        name = getattr(message, "name", None)
        return str(name) if isinstance(name, str) and name else None

    if isinstance(message, dict):
        name = message.get("name")
        return str(name) if isinstance(name, str) and name else None

    return None


def read_message_metadata(message: Any) -> dict[str, Any]:
    """提取消息对象中的扩展元数据。"""

    if isinstance(message, BaseMessage):
        metadata = dict(getattr(message, "additional_kwargs", {}) or {})
        message_id = getattr(message, "id", None)
        if isinstance(message_id, str) and message_id:
            metadata.setdefault("message_id", message_id)

        if isinstance(message, ToolMessage):
            metadata.setdefault("tool_call_id", message.tool_call_id)
            metadata.setdefault("status", message.status)
            if message.artifact is not None:
                metadata.setdefault("artifact", message.artifact)
        return metadata

    if isinstance(message, dict):
        metadata = message.get("metadata")
        if isinstance(metadata, dict):
            return dict(metadata)
        return {}

    return {}


def message_like_to_chat_message(message: Any) -> ChatMessage | None:
    """把 LangChain 或字典消息规整为项目聊天 Schema。"""

    role = read_message_role(message)
    if role is None:
        return None
    content = read_message_content(message)
    if not content:
        return None

    return ChatMessage(
        role=role,
        content=content,
        name=read_message_name(message),
        metadata=read_message_metadata(message),
    )


def chat_message_to_langchain_message(message: ChatMessage) -> BaseMessage:
    """把项目聊天消息转换为 LangChain 消息对象。"""

    metadata = dict(message.metadata or {})
    common_kwargs: dict[str, Any] = {
        "name": message.name,
        "additional_kwargs": metadata,
    }

    if message.role == "assistant":
        return AIMessage(content=message.content, **common_kwargs)

    if message.role == "system":
        return SystemMessage(content=message.content, **common_kwargs)

    if message.role == "tool":
        tool_call_id = metadata.get("tool_call_id")
        if not isinstance(tool_call_id, str) or not tool_call_id:
            tool_call_id = metadata.get("message_id")
        if not isinstance(tool_call_id, str) or not tool_call_id:
            tool_call_id = "tool-call"

        status = metadata.get("status")
        normalized_status = status if status in {"success", "error"} else "success"
        artifact = metadata.get("artifact")
        return ToolMessage(
            content=message.content,
            tool_call_id=tool_call_id,
            status=normalized_status,
            artifact=artifact,
            **common_kwargs,
        )

    return HumanMessage(content=message.content, **common_kwargs)


def message_like_to_langchain_message(message: Any) -> BaseMessage:
    """把多种消息形态统一转换为 LangChain 消息对象。"""

    if isinstance(message, BaseMessage):
        return message

    normalized = message_like_to_chat_message(message)
    if normalized is None:
        raise ValueError("无法识别的消息格式")
    return chat_message_to_langchain_message(normalized)
