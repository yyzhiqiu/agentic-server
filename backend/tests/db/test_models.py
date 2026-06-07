from __future__ import annotations

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.models.conversation import Conversation


def test_all_core_tables_are_registered_for_alembic() -> None:
    expected_tables = {
        "users",
        "api_keys",
        "conversations",
        "messages",
        "agent_runs",
        "tool_calls",
        "audit_logs",
        "files",
        "documents",
    }
    assert expected_tables.issubset(set(Base.metadata.tables))


def test_models_use_safe_metadata_attribute_name() -> None:
    assert hasattr(Conversation, "metadata_")
    assert "metadata" in Conversation.__table__.c
