from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import pytest

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.db.models.document import Document
from app.schemas.file import FileList, FileRead
from app.services.file_service import FileService


class _FakeSession:
    @asynccontextmanager
    async def begin(self):
        yield self


class _FakeFile:
    def __init__(
        self,
        *,
        id: str,
        filename: str,
        content_type: str | None,
        storage_key: str | None,
        size: int | None,
        user_id: str | None,
        metadata_: dict,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.filename = filename
        self.content_type = content_type
        self.storage_key = storage_key
        self.size = size
        self.user_id = user_id
        self.metadata_ = metadata_
        self.created_at = created_at or datetime.now(timezone.utc)
        self.deleted_at: datetime | None = None


class _FakeFileRepository:
    def __init__(self) -> None:
        self.items: dict[str, _FakeFile] = {}

    async def add(self, file) -> _FakeFile:
        file.id = file.id or f"file-{len(self.items) + 1}"
        if file.created_at is None:
            file.created_at = datetime.now(timezone.utc)
        self.items[file.id] = file
        return file

    async def list_by_user(self, user_id: str, *, limit: int = 50, offset: int = 0) -> list[_FakeFile]:
        items = [
            item
            for item in self.items.values()
            if item.user_id == user_id and item.deleted_at is None
        ]
        return items[offset : offset + limit]

    async def count_by_user(self, user_id: str) -> int:
        items = [
            item
            for item in self.items.values()
            if item.user_id == user_id and item.deleted_at is None
        ]
        return len(items)

    async def get_by_id_for_user(self, file_id: str, user_id: str) -> _FakeFile | None:
        item = self.items.get(file_id)
        if item is None or item.user_id != user_id or item.deleted_at is not None:
            return None
        return item

    async def soft_delete(self, file: _FakeFile) -> _FakeFile:
        file.deleted_at = datetime.now(timezone.utc)
        return file


class _FakeDocumentRepository:
    def __init__(self) -> None:
        self.items: dict[str, Document] = {}

    async def add(self, document: Document) -> Document:
        document.id = document.id or f"document-{len(self.items) + 1}"
        if document.created_at is None:
            now = datetime.now(timezone.utc)
            document.created_at = now
            document.updated_at = now
        self.items[document.id] = document
        return document

    async def list_by_file_id(self, file_id: str) -> list[Document]:
        return [
            item
            for item in self.items.values()
            if item.file_id == file_id and item.deleted_at is None
        ]

    async def soft_delete(self, document: Document) -> Document:
        document.deleted_at = datetime.now(timezone.utc)
        return document


class _FakeAuditWriter:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def write(self, event: AuditEvent) -> None:
        self.events.append(event)


class _FakeObjectStorage:
    backend_name = "local"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        self.objects[key] = data
        return key

    async def get_object(self, key: str) -> bytes:
        return self.objects[key]

    async def delete_object(self, key: str) -> None:
        try:
            del self.objects[key]
        except KeyError as exc:
            raise FileNotFoundError(key) from exc


@pytest.mark.asyncio
async def test_file_service_registers_and_lists_uploads() -> None:
    audit_writer = _FakeAuditWriter()
    object_storage = _FakeObjectStorage()
    document_repository = _FakeDocumentRepository()
    service = FileService(
        session=_FakeSession(),  # type: ignore[arg-type]
        file_repository=_FakeFileRepository(),  # type: ignore[arg-type]
        document_repository=document_repository,  # type: ignore[arg-type]
        object_storage=object_storage,  # type: ignore[arg-type]
        audit_service=AuditService(writer=audit_writer),
    )

    created = await service.register_upload(
        filename="demo.txt",
        content=b"hello world",
        content_type="text/plain",
        size=12,
        user_id="user-1",
    )
    assert isinstance(created, FileRead)
    assert created.id == "file-1"
    assert created.status == "stored"
    assert created.user_id == "user-1"
    assert created.size == 11
    assert created.storage_key is not None
    assert created.metadata["document_id"] == "document-1"
    assert created.metadata["document_status"] == "registered"
    assert object_storage.objects[created.storage_key] == b"hello world"
    assert len(document_repository.items) == 1
    assert document_repository.items["document-1"].file_id == "file-1"
    assert document_repository.items["document-1"].title == "demo.txt"
    assert document_repository.items["document-1"].metadata_["status"] == "registered"
    assert len(audit_writer.events) == 1
    assert audit_writer.events[0].action == AuditAction.FILE_UPLOAD
    assert audit_writer.events[0].result == AuditResult.SUCCESS
    assert audit_writer.events[0].resource_id == "file-1"
    assert audit_writer.events[0].metadata["storage"] == "local"
    assert audit_writer.events[0].metadata["document_id"] == "document-1"
    assert audit_writer.events[0].metadata["document_status"] == "registered"

    listed = await service.list("user-1")
    assert isinstance(listed, FileList)
    assert listed.total == 1
    assert listed.items[0].filename == "demo.txt"
    assert listed.items[0].storage_key == created.storage_key


@pytest.mark.asyncio
async def test_file_service_is_scoped_by_user() -> None:
    service = FileService(
        session=_FakeSession(),  # type: ignore[arg-type]
        file_repository=_FakeFileRepository(),  # type: ignore[arg-type]
        object_storage=_FakeObjectStorage(),  # type: ignore[arg-type]
    )

    await service.register_upload(
        filename="first.txt",
        content=b"a",
        content_type="text/plain",
        size=1,
        user_id="user-1",
    )
    await service.register_upload(
        filename="second.txt",
        content=b"b",
        content_type="text/plain",
        size=1,
        user_id="user-2",
    )

    listed = await service.list("user-1")
    assert listed.total == 1
    assert len(listed.items) == 1
    assert listed.items[0].filename == "first.txt"


@pytest.mark.asyncio
async def test_file_service_reads_metadata_and_downloads_content() -> None:
    object_storage = _FakeObjectStorage()
    service = FileService(
        session=_FakeSession(),  # type: ignore[arg-type]
        file_repository=_FakeFileRepository(),  # type: ignore[arg-type]
        object_storage=object_storage,  # type: ignore[arg-type]
    )

    created = await service.register_upload(
        filename="demo.txt",
        content=b"download me",
        content_type="text/plain",
        size=11,
        user_id="user-1",
    )

    detail = await service.get(created.id, "user-1")
    assert detail.id == created.id
    assert detail.storage_key == created.storage_key

    downloaded = await service.download(created.id, "user-1")
    assert downloaded.filename == "demo.txt"
    assert downloaded.content_type == "text/plain"
    assert downloaded.content == b"download me"


@pytest.mark.asyncio
async def test_file_service_deletes_metadata_and_stored_content() -> None:
    audit_writer = _FakeAuditWriter()
    object_storage = _FakeObjectStorage()
    repository = _FakeFileRepository()
    document_repository = _FakeDocumentRepository()
    service = FileService(
        session=_FakeSession(),  # type: ignore[arg-type]
        file_repository=repository,  # type: ignore[arg-type]
        document_repository=document_repository,  # type: ignore[arg-type]
        object_storage=object_storage,  # type: ignore[arg-type]
        audit_service=AuditService(writer=audit_writer),
    )

    created = await service.register_upload(
        filename="delete-me.txt",
        content=b"remove me",
        content_type="text/plain",
        size=9,
        user_id="user-1",
    )

    deleted = await service.delete(created.id, "user-1")

    assert deleted == {"id": created.id, "status": "deleted"}
    assert created.storage_key not in object_storage.objects
    assert repository.items[created.id].deleted_at is not None
    assert document_repository.items["document-1"].deleted_at is not None
    assert audit_writer.events[-1].action == AuditAction.DELETE
    assert audit_writer.events[-1].metadata["status"] == "deleted"
    assert audit_writer.events[-1].metadata["document_deleted_count"] == 1


@pytest.mark.asyncio
async def test_file_service_delete_succeeds_when_stored_bytes_are_missing() -> None:
    audit_writer = _FakeAuditWriter()
    object_storage = _FakeObjectStorage()
    repository = _FakeFileRepository()
    document_repository = _FakeDocumentRepository()
    service = FileService(
        session=_FakeSession(),  # type: ignore[arg-type]
        file_repository=repository,  # type: ignore[arg-type]
        document_repository=document_repository,  # type: ignore[arg-type]
        object_storage=object_storage,  # type: ignore[arg-type]
        audit_service=AuditService(writer=audit_writer),
    )

    created = await service.register_upload(
        filename="orphaned.txt",
        content=b"gone",
        content_type="text/plain",
        size=4,
        user_id="user-1",
    )
    assert created.storage_key is not None
    object_storage.objects.pop(created.storage_key)

    deleted = await service.delete(created.id, "user-1")

    assert deleted == {"id": created.id, "status": "deleted"}
    assert repository.items[created.id].deleted_at is not None
    assert document_repository.items["document-1"].deleted_at is not None
    assert audit_writer.events[-1].action == AuditAction.DELETE
    assert audit_writer.events[-1].metadata["object_deleted"] is False
    assert audit_writer.events[-1].metadata["document_deleted_count"] == 1
