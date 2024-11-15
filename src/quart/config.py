from __future__ import annotations

import json
from typing import Any
from typing import Callable

from flask.config import Config as FlaskConfig  # noqa: F401
from flask.config import ConfigAttribute as ConfigAttribute  # noqa: F401


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
