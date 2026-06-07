from __future__ import annotations

from collections.abc import Generator

import pytest

from app.api.dependencies import get_file_service
from app.core.config import settings
from app.schemas.file import FileList, FileRead
from app.services.file_service import StoredFileDownload


class InMemoryFileService:
    def __init__(self) -> None:
        self.items: dict[str, FileRead] = {}
        self.last_upload: dict | None = None

    async def register_upload(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
        size: int | None,
        user_id: str,
    ) -> FileRead:
        file_id = f"file-{len(self.items) + 1}"
        self.last_upload = {
            "filename": filename,
            "content": content,
            "content_type": content_type,
            "size": size,
            "user_id": user_id,
        }
        item = FileRead(
            id=file_id,
            filename=filename,
            content_type=content_type,
            storage_key=f"uploads/{file_id}.txt",
            size=size,
            user_id=user_id,
            status="stored",
            metadata={
                "status": "stored",
                "storage": "local",
                "document_id": f"document-{len(self.items) + 1}",
                "document_status": "registered",
            },
        )
        self.items[file_id] = item
        return item

    async def list(self, user_id: str, *, limit: int = 50, offset: int = 0) -> FileList:
        items = [item for item in self.items.values() if item.user_id == user_id]
        return FileList(
            items=items[offset : offset + limit],
            total=len(items),
        )

    async def get(self, file_id: str, user_id: str) -> FileRead:
        item = self.items[file_id]
        assert item.user_id == user_id
        return item

    async def download(self, file_id: str, user_id: str) -> StoredFileDownload:
        item = self.items[file_id]
        assert item.user_id == user_id
        return StoredFileDownload(
            filename=item.filename,
            content_type=item.content_type or "application/octet-stream",
            content=b"downloaded-content",
            storage_key=item.storage_key or f"uploads/{file_id}.bin",
        )

    async def delete(self, file_id: str, user_id: str) -> dict[str, str]:
        item = self.items[file_id]
        assert item.user_id == user_id
        self.items.pop(file_id, None)
        return {"id": file_id, "status": "deleted"}


@pytest.fixture
def file_service(client) -> Generator[InMemoryFileService, None, None]:
    service = InMemoryFileService()
    client.app.dependency_overrides[get_file_service] = lambda: service
    try:
        yield service
    finally:
        client.app.dependency_overrides.pop(get_file_service, None)


def test_upload_file_endpoint(client, file_service: InMemoryFileService) -> None:
    response = client.post(
        "/v1/files/upload",
        files={"file": ("demo.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["id"] == "file-1"
    assert payload["data"]["filename"] == "demo.txt"
    assert payload["data"]["status"] == "stored"
    assert payload["data"]["user_id"] == settings.GUEST_USER_ID
    assert payload["data"]["metadata"]["document_id"] == "document-1"
    assert payload["data"]["metadata"]["document_status"] == "registered"
    assert file_service.last_upload is not None
    assert file_service.last_upload["content"] == b"hello"
    assert file_service.last_upload["size"] == 5


def test_list_files_endpoint(client, file_service: InMemoryFileService) -> None:
    client.post(
        "/v1/files/upload",
        files={"file": ("demo-a.txt", b"a", "text/plain")},
    )
    client.post(
        "/v1/files/upload",
        files={"file": ("demo-b.txt", b"b", "text/plain")},
    )

    response = client.get("/v1/files")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["total"] == 2
    assert len(payload["data"]["items"]) == 2
    assert payload["data"]["items"][0]["user_id"] == settings.GUEST_USER_ID


def test_get_file_and_download_endpoints(client, file_service: InMemoryFileService) -> None:
    created = client.post(
        "/v1/files/upload",
        files={"file": ("demo.txt", b"hello", "text/plain")},
    )
    file_id = created.json()["data"]["id"]

    detail_response = client.get(f"/v1/files/{file_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["success"] is True
    assert detail_payload["data"]["id"] == file_id
    assert detail_payload["data"]["storage_key"] == f"uploads/{file_id}.txt"

    download_response = client.get(f"/v1/files/{file_id}/download")
    assert download_response.status_code == 200
    assert download_response.content == b"downloaded-content"
    assert download_response.headers["content-type"].startswith("text/plain")
    assert "attachment;" in download_response.headers["content-disposition"]


def test_delete_file_endpoint(client, file_service: InMemoryFileService) -> None:
    created = client.post(
        "/v1/files/upload",
        files={"file": ("demo.txt", b"hello", "text/plain")},
    )
    file_id = created.json()["data"]["id"]

    response = client.delete(f"/v1/files/{file_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"] == {"id": file_id, "status": "deleted"}

    list_response = client.get("/v1/files")
    assert list_response.json()["data"]["total"] == 0


def test_file_endpoints_isolate_resources_by_api_key(
    client,
    file_service: InMemoryFileService,
) -> None:
    alpha_headers = {"X-API-Key": "alpha-key"}
    beta_headers = {"X-API-Key": "beta-key"}

    first_upload = client.post(
        "/v1/files/upload",
        files={"file": ("alpha.txt", b"alpha", "text/plain")},
        headers=alpha_headers,
    )
    second_upload = client.post(
        "/v1/files/upload",
        files={"file": ("beta.txt", b"beta", "text/plain")},
        headers=beta_headers,
    )

    assert first_upload.status_code == 200
    assert second_upload.status_code == 200

    first_user_id = first_upload.json()["data"]["user_id"]
    second_user_id = second_upload.json()["data"]["user_id"]

    assert first_user_id != second_user_id
    assert first_user_id.startswith(f"{settings.API_KEY_USER_ID_PREFIX}-")
    assert second_user_id.startswith(f"{settings.API_KEY_USER_ID_PREFIX}-")

    alpha_list = client.get("/v1/files", headers=alpha_headers)
    beta_list = client.get("/v1/files", headers=beta_headers)

    assert alpha_list.json()["data"]["total"] == 1
    assert beta_list.json()["data"]["total"] == 1
    assert alpha_list.json()["data"]["items"][0]["filename"] == "alpha.txt"
    assert beta_list.json()["data"]["items"][0]["filename"] == "beta.txt"
