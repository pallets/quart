from typing import Any, AnyStr

from quart.datastructures import MultiDict
from quart.globals import (
    _app_ctx_stack, _request_ctx_stack, current_app, g, request as quart_request, session,
)
from quart.local import LocalProxy
from ._synchronise import sync_with_context


class FlaskRequestProxy(LocalProxy):

    @property
    def form(self) -> MultiDict:
        return sync_with_context(self._get_current_object().form)

    @property
    def files(self) -> MultiDict:
        return sync_with_context(self._get_current_object().files)

    @property
    def json(self) -> Any:
        return sync_with_context(self._get_current_object().json)

    def get_json(self, *args: Any, **kwargs: Any) -> Any:
        return sync_with_context(self._get_current_object().get_json(*args, **kwargs))

    def get_data(self, *args: Any, **kwargs: Any) -> AnyStr:
        return sync_with_context(self._get_current_object().get_data(*args, **kwargs))


request = FlaskRequestProxy(lambda: quart_request)

__all__ = ('_app_ctx_stack', '_request_ctx_stack', 'current_app', 'g', 'request', 'session')
