from __future__ import annotations


def test_validation_error_uses_unified_response(client) -> None:
    response = client.post("/v1/chat", json={})
    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["code"] == "A00001"
    assert "errors" in payload["data"]


def test_not_found_uses_unified_response(client) -> None:
    response = client.get("/missing")
    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["code"] == "A00004"
