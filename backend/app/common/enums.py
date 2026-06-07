from __future__ import annotations

from enum import Enum


class AppEnv(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"
