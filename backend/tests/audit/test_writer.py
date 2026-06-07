from __future__ import annotations

import pytest
from sqlalchemy.orm import SessionTransactionOrigin

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.writer import DatabaseAuditWriter
from tests.support.transactional_session import TransactionalSessionStub


class _FakeSession(TransactionalSessionStub):
    def __init__(
        self,
        *,
        origin: SessionTransactionOrigin | None = None,
    ) -> None:
        super().__init__(origin=origin)
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)


@pytest.mark.asyncio
async def test_database_audit_writer_opens_transaction_when_needed() -> None:
    session = _FakeSession()
    writer = DatabaseAuditWriter(session)  # type: ignore[arg-type]

    await writer.write(
        AuditEvent(
            action=AuditAction.CHAT,
            result=AuditResult.SUCCESS,
            actor_id="user-1",
            resource_type="conversation",
            resource_id="conversation-1",
            metadata={"run_id": "run-1"},
        )
    )

    assert session.begin_calls == 1
    assert session.commit_calls == 1
    assert len(session.added) == 1
    assert session.added[0].action == "chat"
    assert session.added[0].metadata_ == {"run_id": "run-1"}


@pytest.mark.asyncio
async def test_database_audit_writer_commits_owned_autobegin_transaction() -> None:
    session = _FakeSession(origin=SessionTransactionOrigin.AUTOBEGIN)
    writer = DatabaseAuditWriter(session)  # type: ignore[arg-type]

    await writer.write(
        AuditEvent(
            action=AuditAction.CHAT,
            result=AuditResult.SUCCESS,
            actor_id="user-1",
            resource_type="conversation",
            resource_id="conversation-1",
            metadata={"run_id": "run-2"},
        )
    )

    assert session.begin_calls == 0
    assert session.commit_calls == 1
    assert session.rollback_calls == 0
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_database_audit_writer_reuses_explicit_transaction_without_committing() -> None:
    session = _FakeSession(origin=SessionTransactionOrigin.BEGIN)
    writer = DatabaseAuditWriter(session)  # type: ignore[arg-type]

    await writer.write(
        AuditEvent(
            action=AuditAction.CHAT,
            result=AuditResult.SUCCESS,
            actor_id="user-1",
            resource_type="conversation",
            resource_id="conversation-1",
            metadata={"run_id": "run-3"},
        )
    )

    assert session.begin_calls == 0
    assert session.commit_calls == 0
    assert session.rollback_calls == 0
    assert len(session.added) == 1
