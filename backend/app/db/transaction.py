"""Shared transaction helpers for service-level write boundaries."""

from __future__ import annotations

from collections.abc import AsyncIterator, MutableMapping
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import SessionTransactionOrigin


_OWNED_AUTOBEGIN_KEY = "app.db.transaction.owned_autobegin"


def _transaction_state_store(session: AsyncSession) -> MutableMapping[str, Any]:
    """Return a mutable store for helper-owned transaction state.

    Real ``AsyncSession`` instances expose ``session.info`` for request-scoped
    metadata. The tests in this repository often use lightweight fake sessions,
    so the helper falls back to an ad-hoc attribute store when ``info`` is not
    available.
    """

    info = getattr(session, "info", None)
    if info is not None:
        return info

    store = getattr(session, "_transaction_state", None)
    if store is None:
        store = {}
        setattr(session, "_transaction_state", store)
    return store


def _transaction_origin(session: AsyncSession) -> SessionTransactionOrigin | None:
    """Return the current root transaction origin when the session has one."""

    get_transaction = getattr(session, "get_transaction", None)
    if get_transaction is None:
        return None

    transaction = get_transaction()
    if transaction is None:
        return None

    sync_transaction = getattr(transaction, "sync_transaction", transaction)
    origin = getattr(sync_transaction, "origin", None)
    if isinstance(origin, SessionTransactionOrigin):
        return origin
    return None


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Provide a safe service-layer transaction boundary for one session.

    SQLAlchemy 2.x automatically enters an ``AUTOBEGIN`` transaction on the
    first read. This helper adopts that implicit transaction when a later write
    scope is requested, so read-then-write flows can still commit or roll back
    as one unit. If the caller already owns an explicit transaction, the helper
    simply reuses it and avoids creating nested ``session.begin()`` blocks.
    """

    store = _transaction_state_store(session)
    if store.get(_OWNED_AUTOBEGIN_KEY):
        yield session
        return

    origin = _transaction_origin(session)
    if origin is None:
        async with session.begin():
            yield session
        return

    if origin is SessionTransactionOrigin.AUTOBEGIN:
        store[_OWNED_AUTOBEGIN_KEY] = True
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
        finally:
            store.pop(_OWNED_AUTOBEGIN_KEY, None)
        return

    yield session
