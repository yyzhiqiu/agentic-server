from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from app.integrations.object_storage import LocalObjectStorage


@pytest.mark.asyncio
async def test_local_object_storage_puts_and_gets_bytes() -> None:
    root = Path.cwd() / "backend" / ".tmp_object_storage" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    try:
        storage = LocalObjectStorage(root)

        key = await storage.put_object(
            "uploads/user-1/demo.txt",
            b"hello world",
            content_type="text/plain",
        )
        content = await storage.get_object(key)

        assert key == "uploads/user-1/demo.txt"
        assert content == b"hello world"
        assert (root / "uploads" / "user-1" / "demo.txt").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_local_object_storage_rejects_parent_path_escape() -> None:
    root = Path.cwd() / "backend" / ".tmp_object_storage" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    try:
        storage = LocalObjectStorage(root)

        with pytest.raises(ValueError):
            await storage.put_object("../escape.txt", b"nope")
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_local_object_storage_deletes_bytes() -> None:
    root = Path.cwd() / "backend" / ".tmp_object_storage" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    try:
        storage = LocalObjectStorage(root)
        key = await storage.put_object("uploads/user-1/demo.txt", b"hello")

        await storage.delete_object(key)

        assert not (root / "uploads" / "user-1" / "demo.txt").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)
