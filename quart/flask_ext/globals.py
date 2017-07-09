from typing import Any, AnyStr

from multidict import MultiDict

from quart.globals import (
    _app_ctx_stack, _request_ctx_stack, current_app, g, request as quart_request, session,
)
from quart.json import loads
from quart.local import LocalProxy


class FlaskRequestProxy(LocalProxy):

    @property
    def form(self) -> MultiDict:
        return self._get_current_object()._form

    @property
    def files(self) -> MultiDict:
        return self._get_current_object()._files

    @property
    def json(self) -> Any:
        return self.get_json()

    def get_json(self, force: bool=False, silent: bool=False, cache: bool=True) -> Any:
        request_ = self._get_current_object()

        if not (force or request_.is_json):
            return None

        try:
            result = loads(request_._flask_data.decode(request_.charset))
        except ValueError as error:
            if silent:
                result = None
            else:
                request_.on_json_loading_failed(error)
        return result

    def get_data(self, raw: bool=True) -> AnyStr:
        data = self._get_current_object()._flask_data
        if raw:
            return data
        else:
            return data.decode(self._get_current_object().charset)


request = FlaskRequestProxy(lambda: quart_request)

__all__ = ('_app_ctx_stack', '_request_ctx_stack', 'current_app', 'g', 'request', 'session')
