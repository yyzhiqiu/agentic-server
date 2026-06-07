"""文件上传流程使用的对象存储集成。

当前后端先提供基于本地文件系统的轻量实现，方便本地开发和测试阶段持久化
二进制文件。后续如切换到 S3、OSS 或其他对象存储，只需复用同一协议，
无需改动文件服务层对外契约。
"""

from __future__ import annotations

import asyncio
from pathlib import Path, PurePosixPath
from typing import Protocol

from app.core.config import BASE_DIR, settings


class ObjectStorage(Protocol):
    """可插拔二进制对象存储后端需要实现的协议。"""

    backend_name: str

    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """持久化对象并返回最终存储键。"""

    async def get_object(self, key: str) -> bytes:
        """根据存储键读取对象内容。"""

    async def delete_object(self, key: str) -> None:
        """根据存储键删除对象。"""


class NotConfiguredObjectStorage:
    """文件存储关闭时使用的兜底后端。"""

    backend_name = "disabled"

    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        raise NotImplementedError("Object storage is not configured")

    async def get_object(self, key: str) -> bytes:
        raise NotImplementedError("Object storage is not configured")

    async def delete_object(self, key: str) -> None:
        raise NotImplementedError("Object storage is not configured")


class LocalObjectStorage:
    """将二进制对象持久化到配置指定的本地目录。"""

    backend_name = "local"

    def __init__(self, root: Path) -> None:
        self.root = root

    def _resolve_key_path(self, key: str) -> Path:
        """将存储键映射为存储根目录内的安全文件路径。"""

        normalized_key = PurePosixPath(key)
        if normalized_key.is_absolute() or ".." in normalized_key.parts:
            raise ValueError("Object storage key must stay within the storage root")
        return self.root.joinpath(*normalized_key.parts)

    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """将对象写入本地存储根目录。

        当前本地后端只保存原始字节内容。这里保留 ``content_type`` 参数，
        是为了与未来远程存储后端保持一致的接口签名，但文件系统实现本身
        不直接使用该值。
        """

        target = self._resolve_key_path(key)
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_bytes, data)
        return key

    async def get_object(self, key: str) -> bytes:
        """从本地存储根目录读取原始字节内容。"""

        target = self._resolve_key_path(key)
        return await asyncio.to_thread(target.read_bytes)

    async def delete_object(self, key: str) -> None:
        """从本地存储根目录删除对象。"""

        target = self._resolve_key_path(key)
        await asyncio.to_thread(target.unlink)


def _resolve_local_root(raw_root: str) -> Path:
    """将配置中的存储根目录解析为相对 backend 基目录的绝对路径。"""

    root = Path(raw_root).expanduser()
    if root.is_absolute():
        return root
    return BASE_DIR / root


async def check_object_storage_availability(storage: object | None) -> bool | None:
    """检查当前配置的对象存储后端是否可用。

    返回：
        当对象存储被配置为主动关闭时返回 ``None``。
        当后端可访问，或本地根目录可成功创建时返回 ``True``。
        当后端已启用但缺失或不健康时返回 ``False``。

    副作用：
        对于本地后端，这里可能会提前创建配置的根目录，确保健康检查结果
        反映出进程在文件上传开始前是否真的有能力准备好存储位置。
    """

    if settings.OBJECT_STORAGE_BACKEND == "disabled":
        return None
    if storage is None:
        return False
    if isinstance(storage, NotConfiguredObjectStorage):
        return False
    if isinstance(storage, LocalObjectStorage):
        try:
            await asyncio.to_thread(storage.root.mkdir, parents=True, exist_ok=True)
            return await asyncio.to_thread(storage.root.is_dir)
        except OSError:
            return False
    return True


def create_object_storage() -> ObjectStorage:
    """在应用启动阶段创建当前配置的对象存储后端。"""

    if settings.OBJECT_STORAGE_BACKEND == "disabled":
        return NotConfiguredObjectStorage()
    if settings.OBJECT_STORAGE_BACKEND == "local":
        return LocalObjectStorage(_resolve_local_root(settings.OBJECT_STORAGE_LOCAL_ROOT))
    return NotConfiguredObjectStorage()
