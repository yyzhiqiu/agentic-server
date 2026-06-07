from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.db.models.agent_run import AgentRun
from app.db.models.conversation import Conversation
from app.db.models.document import Document
from app.db.models.file import File
from app.db.models.message import Message
from app.db.models.tool_call import ToolCall
from app.db.repositories.base import BaseRepository
from app.db.repositories.agent_run_repo import AgentRunRepository
from app.db.repositories.conversation_repo import ConversationRepository
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.file_repo import FileRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.repositories.tool_call_repo import ToolCallRepository


class _ScalarExecuteResult:
    def __init__(self, items) -> None:
        self.items = items

    def scalars(self):
        return self

    def all(self):
        return self.items


class _CountExecuteResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


@pytest.mark.asyncio
async def test_base_repository_add_and_delete_flush_without_commit() -> None:
    session = SimpleNamespace(
        add=Mock(),
        flush=AsyncMock(),
        delete=AsyncMock(),
    )
    repo = BaseRepository(session, Conversation)  # type: ignore[arg-type]
    conversation = Conversation(title="demo")

    added = await repo.add(conversation)
    assert added is conversation
    session.add.assert_called_once_with(conversation)
    session.flush.assert_awaited_once()

    await repo.delete(conversation)
    session.delete.assert_awaited_once_with(conversation)


def test_conversation_repository_targets_conversation_model() -> None:
    repo = ConversationRepository(object())  # type: ignore[arg-type]
    assert repo.model is Conversation


def test_message_repository_targets_message_model() -> None:
    repo = MessageRepository(object())  # type: ignore[arg-type]
    assert repo.model is Message


def test_file_repository_targets_file_model() -> None:
    repo = FileRepository(object())  # type: ignore[arg-type]
    assert repo.model is File


def test_document_repository_targets_document_model() -> None:
    repo = DocumentRepository(object())  # type: ignore[arg-type]
    assert repo.model is Document


def test_agent_run_repository_targets_agent_run_model() -> None:
    repo = AgentRunRepository(object())  # type: ignore[arg-type]
    assert repo.model is AgentRun


def test_tool_call_repository_targets_tool_call_model() -> None:
    repo = ToolCallRepository(object())  # type: ignore[arg-type]
    assert repo.model is ToolCall


@pytest.mark.asyncio
async def test_agent_run_repository_list_by_user_applies_optional_filters() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=_ScalarExecuteResult([])))
    repo = AgentRunRepository(session)  # type: ignore[arg-type]

    await repo.list_by_user(
        "user-1",
        limit=5,
        offset=10,
        status="failed",
        conversation_id="conversation-1",
    )

    statement = session.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert "agent_runs.user_id" in where_sql
    assert "agent_runs.status" in where_sql
    assert "agent_runs.conversation_id" in where_sql


@pytest.mark.asyncio
async def test_agent_run_repository_count_by_user_applies_optional_filters() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=_CountExecuteResult(1)))
    repo = AgentRunRepository(session)  # type: ignore[arg-type]

    count = await repo.count_by_user(
        "user-1",
        status="completed",
        conversation_id="conversation-9",
    )

    statement = session.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert count == 1
    assert "agent_runs.user_id" in where_sql
    assert "agent_runs.status" in where_sql
    assert "agent_runs.conversation_id" in where_sql


@pytest.mark.asyncio
async def test_file_repository_count_by_user_excludes_deleted_rows() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=_CountExecuteResult(3)))
    repo = FileRepository(session)  # type: ignore[arg-type]

    count = await repo.count_by_user("user-1")

    statement = session.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert count == 3
    assert "files.user_id" in where_sql
    assert "files.deleted_at IS NULL" in where_sql


@pytest.mark.asyncio
async def test_file_repository_get_by_id_for_user_excludes_deleted_rows() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)))
    repo = FileRepository(session)  # type: ignore[arg-type]

    await repo.get_by_id_for_user("file-1", "user-1")

    statement = session.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert "files.id" in where_sql
    assert "files.user_id" in where_sql
    assert "files.deleted_at IS NULL" in where_sql


@pytest.mark.asyncio
async def test_file_repository_get_active_by_id_excludes_deleted_rows() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)))
    repo = FileRepository(session)  # type: ignore[arg-type]

    await repo.get_active_by_id("file-1")

    statement = session.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert "files.id" in where_sql
    assert "files.deleted_at IS NULL" in where_sql


@pytest.mark.asyncio
async def test_file_repository_soft_delete_sets_deleted_at_and_flushes() -> None:
    session = SimpleNamespace(flush=AsyncMock())
    repo = FileRepository(session)  # type: ignore[arg-type]
    file = File(filename="demo.txt")

    deleted = await repo.soft_delete(file)

    assert deleted is file
    assert file.deleted_at is not None
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_document_repository_lists_active_documents_for_file() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=_ScalarExecuteResult([])))
    repo = DocumentRepository(session)  # type: ignore[arg-type]

    await repo.list_by_file_id("file-1")

    statement = session.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert "documents.file_id" in where_sql
    assert "documents.deleted_at IS NULL" in where_sql


@pytest.mark.asyncio
async def test_document_repository_get_active_by_id_excludes_deleted_rows() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)))
    repo = DocumentRepository(session)  # type: ignore[arg-type]

    await repo.get_active_by_id("document-1")

    statement = session.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert "documents.id" in where_sql
    assert "documents.deleted_at IS NULL" in where_sql


@pytest.mark.asyncio
async def test_document_repository_soft_delete_sets_deleted_at_and_flushes() -> None:
    session = SimpleNamespace(flush=AsyncMock())
    repo = DocumentRepository(session)  # type: ignore[arg-type]
    document = Document(file_id="file-1", title="demo.txt", content=None, metadata_={})

    deleted = await repo.soft_delete(document)

    assert deleted is document
    assert document.deleted_at is not None
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_tool_call_repository_lists_by_agent_run() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=_ScalarExecuteResult([])))
    repo = ToolCallRepository(session)  # type: ignore[arg-type]

    await repo.list_by_agent_run("run-1")

    statement = session.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert "tool_calls.agent_run_id" in where_sql
