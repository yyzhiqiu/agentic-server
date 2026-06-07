from __future__ import annotations

from pydantic import BaseModel


class UserRead(BaseModel):
    id: str
    name: str
    email: str | None = None
