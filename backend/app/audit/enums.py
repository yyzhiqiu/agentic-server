from __future__ import annotations

from enum import Enum


class AuditAction(str, Enum):
    LOGIN = "login"
    CHAT = "chat"
    TOOL_CALL = "tool_call"
    DELETE = "delete"
    FILE_UPLOAD = "file_upload"
    AGENT_RESUME = "agent_resume"
    AGENT_INTERRUPT = "agent_interrupt"
    AGENT_CANCEL = "agent_cancel"


class AuditResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
