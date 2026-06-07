from __future__ import annotations

from app.core.config import settings
from app.core.security import user_from_api_key


def test_user_from_api_key_returns_guest_identity_when_header_is_missing() -> None:
    user = user_from_api_key(None)

    assert user.id == settings.GUEST_USER_ID
    assert user.name == settings.GUEST_USER_NAME
    assert user.api_key is None
    assert user.is_guest is True
    assert user.is_anonymous is True


def test_user_from_api_key_derives_stable_isolated_identity() -> None:
    first = user_from_api_key("alpha-key")
    second = user_from_api_key("alpha-key")
    third = user_from_api_key("beta-key")

    assert first.id == second.id
    assert first.id != third.id
    assert first.name == first.id
    assert third.name == third.id
    assert first.id.startswith(f"{settings.API_KEY_USER_ID_PREFIX}-")
    assert third.id.startswith(f"{settings.API_KEY_USER_ID_PREFIX}-")
    assert first.api_key == "alpha-key"
    assert third.api_key == "beta-key"


def test_user_from_api_key_treats_blank_values_as_guest_identity() -> None:
    user = user_from_api_key("   ")

    assert user.id == settings.GUEST_USER_ID
    assert user.name == settings.GUEST_USER_NAME
    assert user.api_key is None
