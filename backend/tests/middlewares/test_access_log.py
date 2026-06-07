from __future__ import annotations

import logging


def test_access_log_records_request_metadata(client, caplog) -> None:
    caplog.set_level(logging.INFO, logger="app.access")

    response = client.get("/health")

    assert response.status_code == 200
    assert any(
        "method=GET" in message and "path=/health" in message and "status_code=200" in message
        for message in caplog.messages
    )
