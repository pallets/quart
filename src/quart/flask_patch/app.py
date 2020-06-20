# The aim is to replace the Quart class exception handling defaults to
# allow for Werkzeug HTTPExceptions to be considered in a special way
# (like the quart HTTPException). In addition a Flask reference is
# created.
import asyncio
from typing import Any, Awaitable, Callable, Union

from quart import Response
from quart.app import Quart
from quart.exceptions import HTTPException as QuartHTTPException
from quart.utils import is_coroutine_function

try:
    from werkzeug.exceptions import HTTPException as WerkzeugHTTPException
except ImportError:

    class WerkzeugHTTPException:  # type: ignore
        pass


old_handle_user_exception = Quart.handle_user_exception


async def new_handle_user_exception(
    self: Quart, error: Union[Exception, WerkzeugHTTPException, QuartHTTPException]
) -> Response:
    if isinstance(error, WerkzeugHTTPException):
        return await new_handle_http_exception(self, error)
    else:
        return await old_handle_user_exception(self, error)


Quart.handle_user_exception = new_handle_user_exception  # type: ignore
old_handle_http_exception = Quart.handle_http_exception


async def new_handle_http_exception(
    self: Quart, error: Union[WerkzeugHTTPException, QuartHTTPException]
) -> Response:
    if isinstance(error, WerkzeugHTTPException):
        handler = self._find_exception_handler(error)
        if handler is None:
            werkzeug_response = error.get_response()
            return await self.make_response(
                (
                    werkzeug_response.get_data(),
                    werkzeug_response.status_code,
                    werkzeug_response.headers,
                )
            )
        else:
            return await handler(error)
    else:
        return await old_handle_http_exception(self, error)


Quart.handle_http_exception = new_handle_http_exception  # type: ignore


def new_ensure_async(  # type: ignore
    self, func: Callable[..., Any]
) -> Callable[..., Awaitable[Any]]:
    if is_coroutine_function(func):
        return func
    else:
        return asyncio.coroutine(func)


Quart.ensure_async = new_ensure_async  # type: ignore

Flask = Quart

__all__ = ("Quart",)
