from __future__ import annotations

from app.core.config import settings


def main() -> None:
    print(f"APP_NAME={settings.APP_NAME}")
    print(f"GUEST_USER_ID={settings.GUEST_USER_ID}")
    print(f"API_KEY_USER_ID_PREFIX={settings.API_KEY_USER_ID_PREFIX}")
    print(f"DATABASE_URL configured={bool(settings.DATABASE_URL)}")
    print(f"REDIS_ENABLED={settings.REDIS_ENABLED}")
    print(f"LLM_API_KEY configured={bool(settings.LLM_API_KEY)}")


if __name__ == "__main__":
    main()
