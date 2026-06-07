"""Transaction-aware async session stubs used by backend tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.orm import SessionTransactionOrigin


class _FakeSyncTransaction:
    """Minimal sync transaction object exposing SQLAlchemy's origin field."""

    def __init__(self, origin: SessionTransactionOrigin) -> None:
        self.origin = origin


class _FakeAsyncTransaction:
    """Minimal async transaction proxy matching ``AsyncSession`` expectations."""

    def __init__(self, origin: SessionTransactionOrigin) -> None:
        self.sync_transaction = _FakeSyncTransaction(origin)


class TransactionalSessionStub:
    """Lightweight async-session stub that simulates SQLAlchemy transaction state."""

    def __init__(
        self,
        *,
        origin: SessionTransactionOrigin | None = None,
    ) -> None:
        self.begin_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.flush_calls = 0
        self.info: dict[str, object] = {}
        self._transaction_origin = origin

    def mark_autobegin(self) -> None:
        """Simulate a read operation starting SQLAlchemy's implicit transaction."""

        if self._transaction_origin is None:
            self._transaction_origin = SessionTransactionOrigin.AUTOBEGIN

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[TransactionalSessionStub]:
        """Open an explicit transaction context on the fake session."""

        self.begin_calls += 1
        previous = self._transaction_origin
        self._transaction_origin = SessionTransactionOrigin.BEGIN
        try:
            yield self
        except Exception:
            self.rollback_calls += 1
            self._transaction_origin = previous
            raise
        else:
            self.commit_calls += 1
            self._transaction_origin = previous

    def get_transaction(self) -> _FakeAsyncTransaction | None:
        """Return the current fake transaction proxy, if one exists."""

        if self._transaction_origin is None:
            return None
        return _FakeAsyncTransaction(self._transaction_origin)

    def in_transaction(self) -> bool:
        """Report whether the fake session is currently inside a transaction."""

        return self._transaction_origin is not None

    async def commit(self) -> None:
        """Commit the current fake transaction."""

        self.commit_calls += 1
        self._transaction_origin = None

    async def rollback(self) -> None:
        """Roll back the current fake transaction."""

        self.rollback_calls += 1
        self._transaction_origin = None

    async def flush(self) -> None:
        """Track flush calls performed during a write transaction."""

        self.flush_calls += 1


def maybe_mark_autobegin(session: object | None) -> None:
    """Mark a fake session as implicitly transactional when a test read occurs."""

    if session is None:
        return
    marker = getattr(session, "mark_autobegin", None)
    if callable(marker):
        marker()
