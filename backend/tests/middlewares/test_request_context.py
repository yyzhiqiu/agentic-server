from __future__ import annotations


def test_request_context_headers(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Trace-Id")
    assert response.headers.get("X-Request-Id")
