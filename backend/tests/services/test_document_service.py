"""最小文档索引流程的测试。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.db.models.document import Document
from app.db.models.file import File
from app.services.document_service import DocumentService


class _FakeSession:
    def __init__(self) -> None:
        self.flush = AsyncMock()

    @asynccontextmanager
    async def begin(self):
        yield self


class _FakeDocumentRepository:
    def __init__(self, items: dict[str, Document] | None = None) -> None:
        self.items = items or {}

    async def get_active_by_id(self, document_id: str) -> Document | None:
        document = self.items.get(document_id)
        if document is None or document.deleted_at is not None:
            return None
        return document


class _FakeFileRepository:
    def __init__(self, items: dict[str, File] | None = None) -> None:
        self.items = items or {}

    async def get_active_by_id(self, file_id: str) -> File | None:
        file = self.items.get(file_id)
        if file is None or file.deleted_at is not None:
            return None
        return file


class _FakeObjectStorage:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = objects or {}

    async def get_object(self, key: str) -> bytes:
        try:
            return self.objects[key]
        except KeyError as exc:
            raise FileNotFoundError(key) from exc


class _NotConfiguredObjectStorage:
    async def get_object(self, key: str) -> bytes:
        raise NotImplementedError(key)


def _build_document(*, document_id: str, file_id: str | None) -> Document:
    document = Document(
        file_id=file_id,
        title=None,
        content=None,
        metadata_={"status": "registered"},
    )
    document.id = document_id
    return document


def _build_file(
    *,
    file_id: str,
    filename: str = "demo.txt",
    content_type: str | None = "text/plain",
    storage_key: str | None = "uploads/user-1/demo.txt",
) -> File:
    file = File(
        user_id="user-1",
        filename=filename,
        content_type=content_type,
        storage_key=storage_key,
        size=12,
        metadata_={"document_status": "registered"},
    )
    file.id = file_id
    return file


def _build_service(
    *,
    documents: dict[str, Document] | None = None,
    files: dict[str, File] | None = None,
    object_storage=None,
):
    session = _FakeSession()
    service = DocumentService(
        session=session,  # type: ignore[arg-type]
        document_repository=_FakeDocumentRepository(documents),  # type: ignore[arg-type]
        file_repository=_FakeFileRepository(files),  # type: ignore[arg-type]
        object_storage=object_storage or _FakeObjectStorage(),  # type: ignore[arg-type]
    )
    return service, session


@pytest.mark.asyncio
async def test_document_service_indexes_text_file_and_updates_metadata() -> None:
    document = _build_document(document_id="document-1", file_id="file-1")
    file = _build_file(file_id="file-1")
    service, session = _build_service(
        documents={"document-1": document},
        files={"file-1": file},
        object_storage=_FakeObjectStorage(
            {"uploads/user-1/demo.txt": b"  Hello \n\n   enterprise agent   "}
        ),
    )

    result = await service.index_document("document-1")

    assert result.document_id == "document-1"
    assert result.file_id == "file-1"
    assert result.status == "indexed"
    assert result.content_length == len("Hello enterprise agent")
    assert document.title == "demo.txt"
    assert document.content == "Hello enterprise agent"
    assert document.metadata_["status"] == "indexed"
    assert document.metadata_["content_length"] == len("Hello enterprise agent")
    assert document.metadata_["indexed_from_file_id"] == "file-1"
    assert document.metadata_["content_type"] == "text/plain"
    assert file.metadata_["document_status"] == "indexed"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_document_service_raises_not_found_when_document_is_missing() -> None:
    service, _ = _build_service()

    with pytest.raises(AppException) as exc_info:
        await service.index_document("missing-document")

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    assert exc_info.value.status_code == 404
    assert exc_info.value.data == {"document_id": "missing-document"}


@pytest.mark.asyncio
async def test_document_service_raises_not_found_when_document_has_no_file_link() -> None:
    document = _build_document(document_id="document-1", file_id=None)
    service, _ = _build_service(documents={"document-1": document})

    with pytest.raises(AppException) as exc_info:
        await service.index_document("document-1")

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    assert exc_info.value.status_code == 404
    assert exc_info.value.data == {"document_id": "document-1"}


@pytest.mark.asyncio
async def test_document_service_raises_not_found_when_linked_file_is_missing() -> None:
    document = _build_document(document_id="document-1", file_id="file-404")
    service, _ = _build_service(documents={"document-1": document})

    with pytest.raises(AppException) as exc_info:
        await service.index_document("document-1")

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    assert exc_info.value.status_code == 404
    assert exc_info.value.data == {"file_id": "file-404"}


@pytest.mark.asyncio
async def test_document_service_raises_not_found_when_storage_key_is_missing() -> None:
    document = _build_document(document_id="document-1", file_id="file-1")
    file = _build_file(file_id="file-1", storage_key=None)
    service, _ = _build_service(
        documents={"document-1": document},
        files={"file-1": file},
    )

    with pytest.raises(AppException) as exc_info:
        await service.index_document("document-1")

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    assert exc_info.value.status_code == 404
    assert exc_info.value.data == {"file_id": "file-1"}


@pytest.mark.asyncio
async def test_document_service_raises_not_found_when_stored_bytes_are_missing() -> None:
    document = _build_document(document_id="document-1", file_id="file-1")
    file = _build_file(file_id="file-1")
    service, _ = _build_service(
        documents={"document-1": document},
        files={"file-1": file},
        object_storage=_FakeObjectStorage(),
    )

    with pytest.raises(AppException) as exc_info:
        await service.index_document("document-1")

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    assert exc_info.value.status_code == 404
    assert exc_info.value.data == {"document_id": "document-1", "file_id": "file-1"}


@pytest.mark.asyncio
async def test_document_service_rejects_unsupported_content_type() -> None:
    document = _build_document(document_id="document-1", file_id="file-1")
    file = _build_file(file_id="file-1", content_type="image/png", filename="image.png")
    service, _ = _build_service(
        documents={"document-1": document},
        files={"file-1": file},
        object_storage=_FakeObjectStorage({"uploads/user-1/demo.txt": b"fake-bytes"}),
    )

    with pytest.raises(AppException) as exc_info:
        await service.index_document("document-1")

    assert exc_info.value.code == ErrorCode.SERVICE_UNAVAILABLE
    assert exc_info.value.status_code == 503
    assert exc_info.value.data == {"file_id": "file-1", "content_type": "image/png"}


@pytest.mark.asyncio
async def test_document_service_rejects_non_utf8_content() -> None:
    document = _build_document(document_id="document-1", file_id="file-1")
    file = _build_file(file_id="file-1")
    service, _ = _build_service(
        documents={"document-1": document},
        files={"file-1": file},
        object_storage=_FakeObjectStorage({"uploads/user-1/demo.txt": b"\xff\xfe"}),
    )

    with pytest.raises(AppException) as exc_info:
        await service.index_document("document-1")

    assert exc_info.value.code == ErrorCode.SERVICE_UNAVAILABLE
    assert exc_info.value.status_code == 503
    assert exc_info.value.data == {"file_id": "file-1", "content_type": "text/plain"}


@pytest.mark.asyncio
async def test_document_service_rejects_empty_normalized_content() -> None:
    document = _build_document(document_id="document-1", file_id="file-1")
    file = _build_file(file_id="file-1")
    service, _ = _build_service(
        documents={"document-1": document},
        files={"file-1": file},
        object_storage=_FakeObjectStorage({"uploads/user-1/demo.txt": b" \n\t  "}),
    )

    with pytest.raises(AppException) as exc_info:
        await service.index_document("document-1")

    assert exc_info.value.code == ErrorCode.REQUEST_VALIDATION_ERROR
    assert exc_info.value.status_code == 422
    assert exc_info.value.data == {"file_id": "file-1"}


@pytest.mark.asyncio
async def test_document_service_raises_when_object_storage_is_not_configured() -> None:
    document = _build_document(document_id="document-1", file_id="file-1")
    file = _build_file(file_id="file-1")
    service, _ = _build_service(
        documents={"document-1": document},
        files={"file-1": file},
        object_storage=_NotConfiguredObjectStorage(),
    )

    with pytest.raises(AppException) as exc_info:
        await service.index_document("document-1")

    assert exc_info.value.code == ErrorCode.SERVICE_UNAVAILABLE
    assert exc_info.value.status_code == 503
    assert exc_info.value.data == {"document_id": "document-1", "file_id": "file-1"}
