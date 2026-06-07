"""API 层使用的请求级身份辅助逻辑。"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256

from app.core.config import settings


def _default_guest_user_id() -> str:
    """返回配置中的游客用户 ID。"""

    return settings.GUEST_USER_ID


def _default_guest_user_name() -> str:
    """返回配置中的游客用户展示名。"""

    return settings.GUEST_USER_NAME


def _derive_api_key_user_id(api_key: str) -> str:
    """基于 API Key 派生稳定的用户标识。

    派生标识用于隔离不同 API Key 对应的资源归属，同时避免直接把原始
    API Key 当作资源拥有者标识存储下来。
    """

    material = api_key
    if settings.API_KEY_USER_HASH_SALT:
        material = f"{settings.API_KEY_USER_HASH_SALT}:{api_key}"
    digest = sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{settings.API_KEY_USER_ID_PREFIX}-{digest}"


@dataclass(slots=True)
class CurrentUser:
    """当前请求解析出的标准化用户身份。"""

    id: str = field(default_factory=_default_guest_user_id)
    name: str = field(default_factory=_default_guest_user_name)
    api_key: str | None = None

    @property
    def is_guest(self) -> bool:
        """判断当前身份是否为配置中的游客用户。"""

        return self.id == settings.GUEST_USER_ID

    @property
    def is_anonymous(self) -> bool:
        """兼容旧调用方式的游客身份别名判断。"""

        return self.is_guest


def user_from_api_key(api_key: str | None) -> CurrentUser:
    """根据可选的 ``X-API-Key`` 请求头解析当前请求身份。

    缺失或为空的 API Key 会回退到配置中的游客身份。
    存在的 API Key 会被转换为稳定的派生用户标识，避免不同 Key 默认共享
    同一批资源。
    """

    normalized_key = (api_key or "").strip()
    if not normalized_key:
        return CurrentUser()

    derived_user_id = _derive_api_key_user_id(normalized_key)
    return CurrentUser(id=derived_user_id, name=derived_user_id, api_key=normalized_key)
