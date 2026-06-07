"""文件元数据编排服务。

本服务负责协调上传元数据登记和用户范围文件查询，控制写操作事务边界，
记录尽力而为的审计事件，通过对象存储保存上传的二进制内容，
为后续 RAG 流程预注册最小文档记录，并将元数据持久化委托给 Repository 层。
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.audit.enums import AuditAction, AuditResult
from app.audit.schemas import AuditEvent
from app.audit.service import AuditService
from app.common.context import get_trace_id
from app.common.error_codes import ErrorCode
from app.common.exceptions import AppException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.file import File
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.file_repo import FileRepository
from app.db.transaction import transaction
from app.integrations.object_storage import ObjectStorage
from app.schemas.file import FileList, FileRead
from app.services.user_service import UserService


@dataclass(slots=True)
class StoredFileDownload:
    """文件下载流程返回的二进制负载。"""

    filename: str
    content_type: str
    content: bytes
    storage_key: str


class FileService:
    """编排文件元数据存储、读取与二进制下载流程。"""

    def __init__(
        self,
        *,
        session: AsyncSession,
        file_repository: FileRepository,
        object_storage: ObjectStorage,
        document_repository: DocumentRepository | None = None,
        user_service: UserService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.session = session
        self.file_repository = file_repository
        self.document_repository = document_repository
        self.object_storage = object_storage
        self.user_service = user_service
        self.audit_service = audit_service or AuditService()

    @staticmethod
    def _build_document_metadata(
        *,
        filename: str,
        content_type: str | None,
        size: int,
        storage_key: str,
    ) -> dict[str, Any]:
        """构建文档记录初始写入的元数据。"""

        return {
            "status": "registered",
            "source": "file_upload",
            "filename": filename,
            "content_type": content_type,
            "size": size,
            "storage_key": storage_key,
        }

    @staticmethod
    def _to_read(file: File) -> FileRead:
        """将文件 ORM 实体映射为 API Schema。"""

        metadata = dict(file.metadata_ or {})
        return FileRead(
            id=file.id,
            filename=file.filename,
            content_type=file.content_type,
            storage_key=file.storage_key,
            size=file.size,
            user_id=file.user_id,
            status=str(metadata.get("status", "registered")),
            metadata=metadata,
            created_at=file.created_at,
        )

    async def _get_owned_file(self, file_id: str, user_id: str) -> File:
        """返回归属于指定用户的文件记录，否则抛出用户范围未找到异常。"""

        file = await self.file_repository.get_by_id_for_user(file_id, user_id)
        if file is None:
            raise AppException(
                ErrorCode.NOT_FOUND,
                status_code=404,
                data={"file_id": file_id},
            )
        return file

    @staticmethod
    def _sanitize_segment(value: str) -> str:
        """规范化标识片段，使其可以安全出现在存储键中。"""

        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
        return normalized or "user"

    @classmethod
    def _build_storage_key(cls, user_id: str, filename: str) -> str:
        """为上传文件构建稳定的本地对象存储键。

        生成后的存储键只保留经过清洗的用户片段和安全的文件后缀，
        避免把客户端任意路径信息泄漏到存储布局中，同时保留对排查问题有用的
        扩展名信息。
        """

        suffix = Path(filename).suffix
        safe_suffix = re.sub(r"[^A-Za-z0-9.]+", "", suffix)[:20]
        return f"uploads/{cls._sanitize_segment(user_id)}/{uuid4().hex}{safe_suffix}"

    async def register_upload(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
        size: int | None,
        user_id: str,
    ) -> FileRead:
        """为当前用户登记上传文件元数据。

        参数：
            filename: 客户端提供的文件名。
            content: 上传的二进制内容。
            content_type: 客户端上报的 MIME 类型。
            size: 传输层给出的尽力而为文件大小。服务在持久化元数据时，
                以 ``content`` 的真实字节长度为准。
            user_id: 上传文件的拥有者。

        返回：
            已持久化的文件元数据。

        副作用：
            会将上传内容写入对象存储，在 Service 层控制的事务中新增文件记录
            和最小文档记录，并在写入成功后尽力记录审计事件。
        """

        if self.user_service is not None:
            await self.user_service.ensure_user(user_id, name=user_id)

        measured_size = len(content)
        storage_key = self._build_storage_key(user_id, filename)
        try:
            stored_key = await self.object_storage.put_object(
                storage_key,
                content,
                content_type=content_type,
            )
        except NotImplementedError as exc:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="对象存储尚未配置",
                status_code=503,
                data={"filename": filename},
            ) from exc
        except (OSError, ValueError) as exc:
            raise AppException(
                ErrorCode.INTERNAL_ERROR,
                message="持久化上传文件失败",
                status_code=500,
                data={"filename": filename, "error": str(exc)},
            ) from exc

        async with transaction(self.session):
            file = File(
                user_id=user_id,
                filename=filename,
                content_type=content_type,
                storage_key=stored_key,
                size=measured_size,
                metadata_={
                    "status": "stored",
                    "storage": self.object_storage.backend_name,
                },
            )
            created = await self.file_repository.add(file)
            if self.document_repository is not None:
                document = await self.document_repository.add(
                    Document(
                        file_id=created.id,
                        title=filename,
                        content=None,
                        metadata_=self._build_document_metadata(
                            filename=filename,
                            content_type=content_type,
                            size=measured_size,
                            storage_key=stored_key,
                        ),
                    )
                )
                created.metadata_ = {
                    **dict(created.metadata_ or {}),
                    "document_id": document.id,
                    "document_status": str(document.metadata_.get("status", "registered")),
                }

        await self.audit_service.record(
            AuditEvent(
                action=AuditAction.FILE_UPLOAD,
                result=AuditResult.SUCCESS,
                actor_id=user_id,
                trace_id=get_trace_id(),
                resource_type="file",
                resource_id=created.id,
                metadata={
                    "filename": created.filename,
                    "content_type": created.content_type,
                    "size": created.size,
                    "storage": self.object_storage.backend_name,
                    "storage_key": created.storage_key,
                    "document_id": dict(created.metadata_ or {}).get("document_id"),
                    "document_status": dict(created.metadata_ or {}).get("document_status"),
                },
            )
        )
        return self._to_read(created)

    async def list(
        self,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> FileList:
        """列出当前用户拥有的文件。"""

        files = await self.file_repository.list_by_user(
            user_id,
            limit=limit,
            offset=offset,
        )
        total = await self.file_repository.count_by_user(user_id)
        return FileList(
            items=[self._to_read(file) for file in files],
            total=total,
        )

    async def get(self, file_id: str, user_id: str) -> FileRead:
        """获取当前用户拥有的单条文件元数据记录。"""

        file = await self._get_owned_file(file_id, user_id)
        return self._to_read(file)

    async def download(self, file_id: str, user_id: str) -> StoredFileDownload:
        """读取当前用户拥有文件的已存储二进制内容。

        参数：
            file_id: 已持久化的文件标识。
            user_id: 用于做归属校验的当前调用方用户 ID。

        返回：
            包含文件名、内容类型与原始字节内容的结构化下载负载，
            可直接用于 HTTP 下载响应。

        异常：
            AppException: 当文件不存在、二进制内容未落库，或当前对象存储后端
                无法读取内容时抛出。
        """

        file = await self._get_owned_file(file_id, user_id)
        if not file.storage_key:
            raise AppException(
                ErrorCode.NOT_FOUND,
                message="文件存储内容不可用",
                status_code=404,
                data={"file_id": file_id},
            )

        try:
            content = await self.object_storage.get_object(file.storage_key)
        except NotImplementedError as exc:
            raise AppException(
                ErrorCode.SERVICE_UNAVAILABLE,
                message="对象存储尚未配置",
                status_code=503,
                data={"file_id": file_id, "storage_key": file.storage_key},
            ) from exc
        except FileNotFoundError as exc:
            raise AppException(
                ErrorCode.NOT_FOUND,
                message="文件存储内容不可用",
                status_code=404,
                data={"file_id": file_id, "storage_key": file.storage_key},
            ) from exc
        except (OSError, ValueError) as exc:
            raise AppException(
                ErrorCode.INTERNAL_ERROR,
                message="读取已存储文件失败",
                status_code=500,
                data={"file_id": file_id, "storage_key": file.storage_key, "error": str(exc)},
            ) from exc

        return StoredFileDownload(
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            content=content,
            storage_key=file.storage_key,
        )

    async def delete(self, file_id: str, user_id: str) -> dict[str, str]:
        """软删除当前用户拥有的文件，并移除其二进制内容。

        服务会先删除对象存储中的真实字节，再软删除元数据，
        以避免对象存储短暂失败时出现“元数据已隐藏但孤儿文件仍残留”的状态，
        影响后续重试逻辑。缺失的二进制内容会被视为已删除，不阻塞元数据清理。
        当文件已关联文档记录时，服务会在同一事务中一并软删除这些文档。
        """

        file = await self._get_owned_file(file_id, user_id)
        object_deleted = False
        documents: list[Document] = []

        if file.storage_key:
            try:
                await self.object_storage.delete_object(file.storage_key)
                object_deleted = True
            except FileNotFoundError:
                object_deleted = False
            except NotImplementedError as exc:
                raise AppException(
                    ErrorCode.SERVICE_UNAVAILABLE,
                    message="对象存储尚未配置",
                    status_code=503,
                    data={"file_id": file_id, "storage_key": file.storage_key},
                ) from exc
            except (OSError, ValueError) as exc:
                raise AppException(
                    ErrorCode.INTERNAL_ERROR,
                    message="删除已存储文件失败",
                    status_code=500,
                    data={"file_id": file_id, "storage_key": file.storage_key, "error": str(exc)},
                ) from exc

        if self.document_repository is not None:
            documents = await self.document_repository.list_by_file_id(file_id)

        async with transaction(self.session):
            for document in documents:
                await self.document_repository.soft_delete(document)
            await self.file_repository.soft_delete(file)

        await self.audit_service.record(
            AuditEvent(
                action=AuditAction.DELETE,
                result=AuditResult.SUCCESS,
                actor_id=user_id,
                trace_id=get_trace_id(),
                resource_type="file",
                resource_id=file_id,
                metadata={
                    "status": "deleted",
                    "storage": self.object_storage.backend_name,
                    "storage_key": file.storage_key,
                    "object_deleted": object_deleted,
                    "document_deleted_count": len(documents),
                },
            )
        )
        return {"id": file_id, "status": "deleted"}
