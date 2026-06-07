"""文档处理编排服务。

本服务负责最小可复用的文档处理流程：将上传文件的二进制内容转为已登记的
文档负载，供后续 RAG 或索引流水线继续使用。它通过集中处理文档与文件查询、
对象存储读取、文本抽取与元数据更新，保持任务函数本身足够轻量。
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from app.db.models.document import Document
from app.db.models.file import File
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.file_repo import FileRepository
from app.db.transaction import transaction
from app.integrations.object_storage import ObjectStorage
from app.utils.text import compact_text


@dataclass(slots=True)
class DocumentIndexResult:
    """最小文档索引流程返回的结构化结果。"""

    document_id: str
    file_id: str | None
    status: str
    content_length: int


class DocumentService:
    """编排最小化文档抽取与元数据索引流程。"""

    def __init__(
        self,
        *,
        session: AsyncSession,
        document_repository: DocumentRepository,
        file_repository: FileRepository,
        object_storage: ObjectStorage,
    ) -> None:
        self.session = session
        self.document_repository = document_repository
        self.file_repository = file_repository
        self.object_storage = object_storage

    @staticmethod
    def _ensure_document_is_indexable(document: Document) -> None:
        """校验文档记录是否具备索引资格。"""

        if document.file_id is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                message="Document is not linked to a file",
                status_code=404,
                data={"document_id": document.id},
            )

    @staticmethod
    def _extract_text(file: File, content: bytes) -> str:
        """将上传字节解码为首轮索引使用的规范化文本。

        当前实现为了保持第一步处理流程足够稳定且简单，只支持文本类负载。
        PDF、DOCX、图片等二进制格式后续可以接入更丰富的解析器，而无需改变
        当前服务边界。
        """

        content_type = (file.content_type or "").lower()
        if content_type and content_type not in {
            "text/plain",
            "text/markdown",
            "application/json",
            "application/xml",
            "text/csv",
        }:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="Document parser is not configured for this file type",
                status_code=503,
                data={
                    "file_id": file.id,
                    "content_type": file.content_type,
                },
            )

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="Document parser is not configured for non UTF-8 content",
                status_code=503,
                data={"file_id": file.id, "content_type": file.content_type},
            ) from exc

        normalized = compact_text(text).strip()
        if not normalized:
            raise AppException(
                ErrorCode.REQUEST_VALIDATION_ERROR,
                message="Document content is empty after normalization",
                status_code=422,
                data={"file_id": file.id},
            )
        return normalized

    async def _get_document(self, document_id: str) -> Document:
        """返回一条有效文档记录，找不到时抛出未找到异常。"""

        document = await self.document_repository.get_active_by_id(document_id)
        if document is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"document_id": document_id},
            )
        return document

    async def _get_document_file(self, file_id: str) -> File:
        """返回与文档关联的有效文件记录。"""

        file = await self.file_repository.get_active_by_id(file_id)
        if file is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                message="Linked file is not available",
                status_code=404,
                data={"file_id": file_id},
            )
        if not file.storage_key:
            raise AppException(
                ErrorCode.NOT_FOUND,
                message="Stored file content is not available",
                status_code=404,
                data={"file_id": file_id},
            )
        return file

    async def index_document(self, document_id: str) -> DocumentIndexResult:
        """抽取最小文本内容，并将文档标记为已索引。

        副作用：
            会从对象存储中读取关联文件，将规范化文本写回文档记录，
            并在由 Service 层控制的事务中更新文档元数据。
        """

        document = await self._get_document(document_id)
        self._ensure_document_is_indexable(document)
        assert document.file_id is not None

        file = await self._get_document_file(document.file_id)

        try:
            raw_content = await self.object_storage.get_object(file.storage_key)
        except NotImplementedError as exc:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="Object storage is not configured",
                status_code=503,
                data={"document_id": document_id, "file_id": file.id},
            ) from exc
        except FileNotFoundError as exc:
            raise AppException(
                ErrorCode.NOT_FOUND,
                message="Stored file content is not available",
                status_code=404,
                data={"document_id": document_id, "file_id": file.id},
            ) from exc

        extracted_text = self._extract_text(file, raw_content)

        async with transaction(self.session):
            document.title = document.title or file.filename
            document.content = extracted_text
            document.metadata_ = {
                **dict(document.metadata_ or {}),
                "status": "indexed",
                "content_length": len(extracted_text),
                "indexed_from_file_id": file.id,
                "content_type": file.content_type,
            }
            file.metadata_ = {
                **dict(file.metadata_ or {}),
                "document_status": "indexed",
            }
            await self.session.flush()

        return DocumentIndexResult(
            document_id=document.id,
            file_id=file.id,
            status="indexed",
            content_length=len(extracted_text),
        )
