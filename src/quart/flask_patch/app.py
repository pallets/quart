# The aim is to replace the Quart class exception handling defaults to
# allow for Werkzeug HTTPExceptions to be considered in a special way
# (like the quart HTTPException). In addition a Flask reference is
# created.

try:
    from werkzeug.exceptions import HTTPException
except ImportError:

    class HTTPException:  # type: ignore
        pass


from quart import Response
from quart.app import Quart

old_handle_user_exception = Quart.handle_user_exception


async def new_handle_user_exception(self, error: Exception) -> Response:  # type: ignore
    if isinstance(error, HTTPException):
        return await self.handle_http_exception(error)
    else:
        return await old_handle_user_exception(self, error)


Quart.handle_user_exception = new_handle_user_exception  # type: ignore
old_handle_http_exception = Quart.handle_http_exception


async def new_handle_http_exception(self, error: Exception) -> Response:  # type: ignore
    if isinstance(error, HTTPException):
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

Flask = Quart

__all__ = ("Quart",)
