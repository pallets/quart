from functools import partial
from typing import Any, List  # noqa: F401

from .local import LocalProxy, LocalStack


def _request_ctx_lookup(name: str) -> Any:
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError('Attempt to access request context, outside of a request.')
    return getattr(top, name)


def _app_ctx_lookup(name: str) -> Any:
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError('Attempt to access app context.')
    return getattr(top, name)


class _AppStack:

    def __init__(self) -> None:
        self._stack: List[Any] = []

    def push(self, value: Any) -> None:
        self._stack.append(value)

    def pop(self) -> Any:
        return self._stack.pop()

    @property
    def top(self) -> Any:
        try:
            return self._stack[-1]
        except (AttributeError, IndexError):
            return None


_request_ctx_stack = LocalStack()
_app_ctx_stack = _AppStack()

current_app = LocalProxy(partial(_app_ctx_lookup, 'app'))  # type: ignore
g = LocalProxy(partial(_app_ctx_lookup, 'g'))  # type: ignore
request = LocalProxy(partial(_request_ctx_lookup, 'request'))  # type: ignore
session = LocalProxy(partial(_request_ctx_lookup, 'session'))  # type: ignore
