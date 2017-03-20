import importlib
import json
import os
from datetime import timedelta
from typing import Any, Callable, Optional

DEFAULT_CONFIG = {
    'APPLICATION_ROOT': None,
    'DEBUG': False,
    'JSONIFY_MIMETYPE': 'application/json',
    'JSONIFY_PRETTYPRINT_REGULAR': False,
    'LOGGER_NAME': None,
    'LOGGER_HANDLER_POLICY': 'always',
    'PERMANENT_SESSION_LIFETIME': timedelta(days=31),
    'PREFERRED_URL_SCHEME': 'http',
    'SECRET_KEY': None,
    'SERVER_NAME': None,
    'SESSION_COOKIE_DOMAIN': None,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_NAME': 'session',
    'SESSION_COOKIE_PATH': None,
    'SESSION_COOKIE_SECURE': False,
    'SESSION_REFRESH_EACH_REQUEST': True,
    'TEMPLATES_AUTO_RELOAD': None,
    'TESTING': False,
}


class ConfigAttribute:
    """Implements a property descriptor for objects with a config attribute."""

    def __init__(self, key: str, converter: Optional[Callable]=None) -> None:
        self.key = key
        self.converter = converter

    def __get__(self, instance: object, owner: type=None) -> Any:
        if instance is None:
            return self
        result = instance.config[self.key]  # type: ignore
        if self.converter is not None:
            return self.converter(result)
        else:
            return result

    def __set__(self, instance: object, value: Any) -> None:
        instance.config[self.key] = value  # type: ignore


class Config(dict):

    def __init__(self, root_path: str, defaults: Optional[dict]=None) -> None:
        super().__init__(defaults or {})
        self.root_path = root_path

    def from_object(self, instance: object) -> None:
        if isinstance(instance, str):
            try:
                path, config = instance.rsplit('.', 1)
            except ValueError:
                path = instance
                instance = importlib.import_module(instance)
            else:
                module = importlib.import_module(path)
                instance = getattr(module, config)

        for key in dir(instance):
            if key.isupper():
                self[key] = getattr(instance, key)

    def from_json(self, filename: str, silent: bool=False) -> None:
        file_path = os.path.join(self.root_path, filename)
        try:
            with open(file_path) as file_:
                data = json.loads(file_.read())
        except (FileNotFoundError, IsADirectoryError):
            if not silent:
                raise
        else:
            self.from_mapping(data)

    def from_mapping(self, mapping: Optional[dict]=None, **kwargs: Any) -> None:
        mappings = {}
        if mapping is not None:
            mappings.update(mapping)
        mappings.update(kwargs)
        for key, value in mappings.items():
            if key.isupper():
                self[key] = value
