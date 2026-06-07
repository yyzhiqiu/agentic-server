"""文档索引任务包装层的测试。"""

from __future__ import annotations

import pytest

from app.services.document_service import DocumentIndexResult
from app.tasks import document_indexing


class _FakeDocumentService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def index_document(self, document_id: str) -> DocumentIndexResult:
        self.calls.append(document_id)
        return DocumentIndexResult(
            document_id=document_id,
            file_id="file-1",
            status="indexed",
            content_length=18,
        )


class _FakeSessionContext:
    def __init__(self, session: object) -> None:
        self.session = session

    async def __aenter__(self) -> object:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_index_document_task_serializes_injected_service_result() -> None:
    service = _FakeDocumentService()

    result = await document_indexing.index_document("document-1", service=service)

    assert result == {
        "document_id": "document-1",
        "file_id": "file-1",
        "status": "indexed",
        "content_length": 18,
    }
    assert service.calls == ["document-1"]


@pytest.mark.asyncio
async def test_index_document_task_builds_runtime_service_when_not_injected(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_session = object()
    fake_document_repository = object()
    fake_file_repository = object()
    fake_object_storage = object()

    class _RuntimeDocumentService:
        def __init__(self, *, session, document_repository, file_repository, object_storage) -> None:
            captured["session"] = session
            captured["document_repository"] = document_repository
            captured["file_repository"] = file_repository
            captured["object_storage"] = object_storage

        async def index_document(self, document_id: str) -> DocumentIndexResult:
            captured["document_id"] = document_id
            return DocumentIndexResult(
                document_id=document_id,
                file_id="file-9",
                status="indexed",
                content_length=27,
            )

    monkeypatch.setattr(document_indexing, "AsyncSessionLocal", lambda: _FakeSessionContext(fake_session))
    monkeypatch.setattr(document_indexing, "create_object_storage", lambda: fake_object_storage)
    monkeypatch.setattr(document_indexing, "DocumentRepository", lambda session: fake_document_repository)
    monkeypatch.setattr(document_indexing, "FileRepository", lambda session: fake_file_repository)
    monkeypatch.setattr(document_indexing, "DocumentService", _RuntimeDocumentService)

    result = await document_indexing.index_document("document-9")

    assert result == {
        "document_id": "document-9",
        "file_id": "file-9",
        "status": "indexed",
        "content_length": 27,
    }
    assert captured == {
        "session": fake_session,
        "document_repository": fake_document_repository,
        "file_repository": fake_file_repository,
        "object_storage": fake_object_storage,
        "document_id": "document-9",
    }
