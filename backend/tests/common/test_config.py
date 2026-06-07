from __future__ import annotations

import pytest

from app.core.config import Settings


def test_settings_normalize_identity_related_strings() -> None:
    settings = Settings(
        GUEST_USER_ID=" guest-user ",
        GUEST_USER_NAME=" Guest User ",
        API_KEY_USER_ID_PREFIX=" api-key ",
        CACHE_NAMESPACE=" agent-cache ",
    )

    assert settings.GUEST_USER_ID == "guest-user"
    assert settings.GUEST_USER_NAME == "Guest User"
    assert settings.API_KEY_USER_ID_PREFIX == "api-key"
    assert settings.CACHE_NAMESPACE == "agent-cache"


def test_settings_reject_empty_identity_related_strings() -> None:
    with pytest.raises(ValueError):
        Settings(GUEST_USER_ID="   ")
