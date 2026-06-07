from __future__ import annotations

from app.graph.routing import should_continue


def test_routing_defaults_to_end() -> None:
    assert should_continue({"messages": []}) == "end"
