from __future__ import annotations

from functools import partial
from typing import Any, List  # noqa: F401

from .local import LocalProxy, LocalStack


def _ctx_lookup(ctx_stacks: List[LocalStack], name: str) -> Any:
    top = None
    for ctx_stack in ctx_stacks:
        top = ctx_stack.top
        if top is not None:
            break
    if top is None:
        raise RuntimeError(f"Attempt to access {name} outside of a relevant context")
    return getattr(top, name)


_app_ctx_stack = LocalStack()
_request_ctx_stack = LocalStack()
_websocket_ctx_stack = LocalStack()

current_app = LocalProxy(partial(_ctx_lookup, [_app_ctx_stack], "app"))
g = LocalProxy(partial(_ctx_lookup, [_app_ctx_stack], "g"))
request = LocalProxy(partial(_ctx_lookup, [_request_ctx_stack], "request"))
session = LocalProxy(partial(_ctx_lookup, [_request_ctx_stack, _websocket_ctx_stack], "session"))
websocket = LocalProxy(partial(_ctx_lookup, [_websocket_ctx_stack], "websocket"))
