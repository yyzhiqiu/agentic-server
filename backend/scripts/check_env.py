from __future__ import annotations

from app.core.config import settings


def main() -> None:
    print(f"应用名称 APP_NAME={settings.APP_NAME}")
    print(f"访客用户 ID GUEST_USER_ID={settings.GUEST_USER_ID}")
    print(f"API Key 用户前缀 API_KEY_USER_ID_PREFIX={settings.API_KEY_USER_ID_PREFIX}")
    print(f"数据库地址是否已配置 DATABASE_URL={bool(settings.DATABASE_URL)}")
    print(f"是否启用 Redis REDIS_ENABLED={settings.REDIS_ENABLED}")
    print(f"LLM_API_KEY 是否已配置={bool(settings.LLM_API_KEY)}")


if __name__ == "__main__":
    main()
