"""文档索引任务入口。

本模块保持异步任务包装层足够轻量，把真正的文档处理流程委托给
``DocumentService``。任务既可以复用 Worker 运行时注入的服务实例，
也可以为简单本地执行场景自行构建最小运行时。
"""

from __future__ import annotations

from typing import Any

from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.file_repo import FileRepository
from app.db.session import AsyncSessionLocal
from app.integrations.object_storage import create_object_storage
from app.services.document_service import DocumentService


async def index_document(
    document_id: str,
    *,
    service: DocumentService | None = None,
) -> dict[str, Any]:
    """将文档索引为规范化文本内容。

    参数：
        document_id: 需要处理的有效文档记录 ID。
        service: 可选的预构建服务实例，适用于已经自行管理数据库会话和
            对象存储资源的 Worker 运行时。

    返回：
        描述本次处理结果的小型序列化任务结果。
    """

    if service is not None:
        result = await service.index_document(document_id)
        return {
            "document_id": result.document_id,
            "file_id": result.file_id,
            "status": result.status,
            "content_length": result.content_length,
        }

    object_storage = create_object_storage()
    async with AsyncSessionLocal() as session:
        runtime_service = DocumentService(
            session=session,
            document_repository=DocumentRepository(session),
            file_repository=FileRepository(session),
            object_storage=object_storage,
        )
        result = await runtime_service.index_document(document_id)
    return {
        "document_id": result.document_id,
        "file_id": result.file_id,
        "status": result.status,
        "content_length": result.content_length,
    }
