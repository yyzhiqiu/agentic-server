from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from app.common.context import get_trace_id


@contextmanager
def trace_operation(name: str, **attributes: object) -> Iterator[dict[str, object]]:
    span = {"name": name, "trace_id": get_trace_id(), "attributes": attributes}
    yield span
