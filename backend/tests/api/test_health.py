from __future__ import annotations

import pytest

from app.api.v1 import health as health_module
from app.integrations.object_storage import NotConfiguredObjectStorage


def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"


@pytest.mark.usefixtures("client")
def test_ready_reports_object_storage_when_available(client, monkeypatch) -> None:
    async def database_ready() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_database_connection", database_ready)
    monkeypatch.setattr(health_module.settings, "REDIS_ENABLED", False)
    monkeypatch.setattr(health_module.settings, "OBJECT_STORAGE_BACKEND", "local")

    response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ready"
    assert "database" in payload["data"]
    assert "redis" in payload["data"]
    assert "graph" in payload["data"]
    assert "object_storage" in payload["data"]
    assert payload["data"]["object_storage"] == {
        "backend": "local",
        "configured": True,
        "available": True,
    }


def test_ready_is_degraded_when_object_storage_is_enabled_but_missing(client, monkeypatch) -> None:
    async def database_ready() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_database_connection", database_ready)
    monkeypatch.setattr(health_module.settings, "REDIS_ENABLED", False)
    monkeypatch.setattr(health_module.settings, "OBJECT_STORAGE_BACKEND", "local")

    original_storage = getattr(client.app.state, "object_storage", None)
    client.app.state.object_storage = None
    try:
        response = client.get("/ready")
    finally:
        client.app.state.object_storage = original_storage

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "degraded"
    assert payload["data"]["object_storage"] == {
        "backend": "local",
        "configured": True,
        "available": False,
    }


def test_ready_keeps_status_ready_when_object_storage_is_disabled(client, monkeypatch) -> None:
    async def database_ready() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_database_connection", database_ready)
    monkeypatch.setattr(health_module.settings, "REDIS_ENABLED", False)
    monkeypatch.setattr(health_module.settings, "OBJECT_STORAGE_BACKEND", "disabled")

    original_storage = getattr(client.app.state, "object_storage", None)
    client.app.state.object_storage = NotConfiguredObjectStorage()
    try:
        response = client.get("/ready")
    finally:
        client.app.state.object_storage = original_storage

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ready"
    assert payload["data"]["object_storage"] == {
        "backend": "disabled",
        "configured": False,
        "available": None,
    }
