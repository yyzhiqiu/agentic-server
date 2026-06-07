from __future__ import annotations

import httpx


def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(30.0))


async def close_http_client(client: httpx.AsyncClient | None) -> None:
    if client is not None:
        await client.aclose()
