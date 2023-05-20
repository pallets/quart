from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Callable

from flask.config import Config as FlaskConfig, ConfigAttribute as ConfigAttribute  # noqa: F401

DEFAULT_CONFIG = {
    "APPLICATION_ROOT": None,
    "BODY_TIMEOUT": 60,  # Second
    "DEBUG": None,
    "ENV": None,
    "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16 MB Limit
    "MAX_COOKIE_SIZE": 4093,
    "PERMANENT_SESSION_LIFETIME": timedelta(days=31),
    "PREFER_SECURE_URLS": False,  # Replaces PREFERRED_URL_SCHEME to allow for WebSocket scheme
    "PRESERVE_CONTEXT_ON_EXCEPTION": None,
    "PROPAGATE_EXCEPTIONS": None,
    "RESPONSE_TIMEOUT": 60,  # Second
    "SECRET_KEY": None,
    "SEND_FILE_MAX_AGE_DEFAULT": timedelta(hours=12),
    "SERVER_NAME": None,
    "SESSION_COOKIE_DOMAIN": None,
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_NAME": "session",
    "SESSION_COOKIE_PATH": None,
    "SESSION_COOKIE_SAMESITE": None,
    "SESSION_COOKIE_SECURE": False,
    "SESSION_REFRESH_EACH_REQUEST": True,
    "TEMPLATES_AUTO_RELOAD": None,
    "TESTING": False,
    "TRAP_HTTP_EXCEPTIONS": False,
}


class Config(FlaskConfig):
    def from_prefixed_env(
        self, prefix: str = "QUART", *, loads: Callable[[str], Any] = json.loads
    ) -> bool:
        """Load any environment variables that start with the prefix.

        The prefix (default ``QUART_``) is dropped from the env key
        for the config key. Values are passed through a loading
        function to attempt to convert them to more specific types
        than strings.

        Keys are loaded in :func:`sorted` order.

        The default loading function attempts to parse values as any
        valid JSON type, including dicts and lists.  Specific items in
        nested dicts can be set by separating the keys with double
        underscores (``__``). If an intermediate key doesn't exist, it
        will be initialized to an empty dict.

        Arguments:
            prefix: Load env vars that start with this prefix,
                separated with an underscore (``_``).
            loads: Pass each string value to this function and use the
                returned value as the config value. If any error is
                raised it is ignored and the value remains a
                string. The default is :func:`json.loads`.
        """
        return super().from_prefixed_env(prefix, loads=loads)
