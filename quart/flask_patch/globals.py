import asyncio
from typing import Any, AnyStr

from quart.datastructures import MultiDict
from quart.globals import (
    _app_ctx_stack, _request_ctx_stack, current_app, g, request as quart_request, session,
)
from quart.local import LocalProxy


class FlaskRequestProxy(LocalProxy):

    @property
    def form(self) -> MultiDict:
        return asyncio.get_event_loop().sync_wait(self._get_current_object().form)  # type: ignore

    @property
    def files(self) -> MultiDict:
        return asyncio.get_event_loop().sync_wait(self._get_current_object().files)  # type: ignore

    @property
    def json(self) -> Any:
        return asyncio.get_event_loop().sync_wait(self._get_current_object().json)  # type: ignore

    def get_json(self, *args: Any, **kwargs: Any) -> Any:
        return asyncio.get_event_loop().sync_wait(  # type: ignore
            self._get_current_object().get_json(*args, **kwargs),
        )

    def get_data(self, *args: Any, **kwargs: Any) -> AnyStr:
        return asyncio.get_event_loop().sync_wait(  # type: ignore
            self._get_current_object().get_data(*args, **kwargs),
        )


request = FlaskRequestProxy(lambda: quart_request)

__all__ = ('_app_ctx_stack', '_request_ctx_stack', 'current_app', 'g', 'request', 'session')
