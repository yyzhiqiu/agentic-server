"""文件元数据相关接口。

API 层负责接收 multipart 上传请求、读取二进制内容，并将存储和元数据持久化
委托给 Service 层处理。
"""

from __future__ import annotations

from urllib.parse import quote
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.api.dependencies import get_current_user, get_file_service
from app.common.responses import success_response
from app.core.security import CurrentUser
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])


@router.get("")
async def list_files(
    limit: int = 50,
    offset: int = 0,
    service: FileService = Depends(get_file_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """列出当前用户可见的文件元数据。"""

    data = await service.list(user.id, limit=limit, offset=offset)
    return success_response(data.model_dump())


@router.get("/{file_id}")
async def get_file(
    file_id: str,
    service: FileService = Depends(get_file_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """获取当前用户可见的文件元数据。"""

    data = await service.get(file_id, user.id)
    return success_response(data.model_dump())


@router.post("/upload")
async def upload_file(
    file: Annotated[UploadFile, File()],
    service: FileService = Depends(get_file_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """保存上传文件，并为当前用户持久化对应元数据。"""

    content = await file.read()

    data = await service.register_upload(
        filename=file.filename or "unknown",
        content=content,
        content_type=file.content_type,
        size=len(content),
        user_id=user.id,
    )
    return success_response(data.model_dump())


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    service: FileService = Depends(get_file_service),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """下载当前用户可见的已存储文件内容。"""

    file = await service.download(file_id, user.id)
    quoted_filename = quote(file.filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}",
    }
    return Response(
        content=file.content,
        media_type=file.content_type,
        headers=headers,
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    service: FileService = Depends(get_file_service),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """软删除当前用户拥有的文件。"""

    return success_response(await service.delete(file_id, user.id))
