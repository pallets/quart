import asyncio
import warnings
from contextvars import copy_context
from datetime import datetime, timedelta, timezone
from functools import partial, wraps
from http.cookies import CookieError, SimpleCookie
from os import PathLike
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional, TYPE_CHECKING, Union
from wsgiref.handlers import format_date_time

from .globals import current_app
from .typing import FilePath

if TYPE_CHECKING:
    from .wrappers.response import Response  # noqa: F401


def redirect(location: str, status_code: int = 302) -> "Response":
    body = f"""
<!doctype html>
<title>Redirect</title>
<h1>Redirect</h1>
You should be redirected to <a href="{location}">{location}</a>, if not please click the link
    """

    return current_app.response_class(body, status=status_code, headers={"Location": location})


def create_cookie(
    key: str,
    value: str = "",
    max_age: Optional[Union[int, timedelta]] = None,
    expires: Optional[Union[int, float, datetime]] = None,
    path: str = "/",
    domain: Optional[str] = None,
    secure: bool = False,
    httponly: bool = False,
    samesite: str = None,
) -> SimpleCookie:
    """Create a Cookie given the options set

    The arguments are the standard cookie morsels and this is a
    wrapper around the stdlib SimpleCookie code.
    """
    cookie: SimpleCookie = SimpleCookie()
    cookie[key] = value
    cookie[key]["path"] = path
    cookie[key]["httponly"] = httponly
    cookie[key]["secure"] = secure
    if isinstance(max_age, timedelta):
        cookie[key]["max-age"] = f"{max_age.total_seconds():d}"
    if isinstance(max_age, int):
        cookie[key]["max-age"] = str(max_age)
    if expires is not None and isinstance(expires, (int, float)):
        cookie[key]["expires"] = format_date_time(int(expires))
    elif expires is not None and isinstance(expires, datetime):
        cookie[key]["expires"] = format_date_time(expires.replace(tzinfo=timezone.utc).timestamp())
    if domain is not None:
        cookie[key]["domain"] = domain
    if samesite is not None:
        try:
            cookie[key]["samesite"] = samesite
        except CookieError:
            warnings.warn(
                "Samesite cookies are not supported in this Python version, "
                "please upgrade to >= 3.8"
            )
    return cookie


def ensure_coroutine(func: Callable) -> Callable:
    warnings.warn(
        "Please switch to using a coroutine function. "
        "Synchronous functions will not be supported in 0.13 onwards.",
        DeprecationWarning,
    )
    if asyncio.iscoroutinefunction(func):
        return func
    else:
        async_func = asyncio.coroutine(func)
        async_func._quart_async_wrapper = True  # type: ignore
        return async_func


def file_path_to_path(*paths: FilePath) -> Path:
    # Flask supports bytes paths
    safe_paths: List[Union[str, PathLike]] = []
    for path in paths:
        if isinstance(path, bytes):
            safe_paths.append(path.decode())
        else:
            safe_paths.append(path)
    return Path(*safe_paths)


def run_sync(func: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    """Ensure that the sync function is run within the event loop.

    If the *func* is not a coroutine it will be wrapped such that
    it runs in the default executor (use loop.set_default_executor
    to change). This ensures that synchronous functions do not
    block the event loop.
    """

    @wraps(func)
    async def _wrapper(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, copy_context().run, partial(func, *args, **kwargs))

    _wrapper._quart_async_wrapper = True  # type: ignore
    return _wrapper
