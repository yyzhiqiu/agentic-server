from __future__ import annotations

import logging

from app.core.config import settings


def test_audit_log_records_request_context(client, caplog) -> None:
    caplog.set_level(logging.INFO, logger="app.audit.middleware")

    response = client.get("/health")

    assert response.status_code == 200
    assert any(
        "method=GET" in message
        and "path=/health" in message
        and settings.GUEST_USER_ID in message
        for message in caplog.messages
    )
