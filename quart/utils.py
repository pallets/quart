import asyncio
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from typing import Callable, Optional, TYPE_CHECKING, Union
from wsgiref.handlers import format_date_time

from .globals import current_app

if TYPE_CHECKING:
    from .wrappers.response import Response  # noqa: F401


def redirect(location: str, status_code: int=302) -> 'Response':
    body = f"""
<!doctype html>
<title>Redirect</title>
<h1>Redirect</h1>
You should be redirected to <a href="{location}">{location}</a>, if not please click the link
    """

    return current_app.response_class(
        body, status=status_code, headers={'Location': location},
    )


def create_cookie(
        key: str,
        value: str='',
        max_age: Optional[Union[int, timedelta]]=None,
        expires: Optional[Union[int, float, datetime]]=None,
        path: str='/',
        domain: Optional[str]=None,
        secure: bool=False,
        httponly: bool=False,
) -> SimpleCookie:
    """Create a Cookie given the options set

    The arguments are the standard cookie morsels and this is a
    wrapper around the stdlib SimpleCookie code.
    """
    cookie = SimpleCookie()  # type: ignore
    cookie[key] = value
    cookie[key]['path'] = path
    cookie[key]['httponly'] = httponly  # type: ignore
    cookie[key]['secure'] = secure  # type: ignore
    if isinstance(max_age, timedelta):
        cookie[key]['max-age'] = f"{max_age.total_seconds():d}"  # type: ignore
    if isinstance(max_age, int):
        cookie[key]['max-age'] = str(max_age)
    if expires is not None and isinstance(expires, (int, float)):
        cookie[key]['expires'] = format_date_time(int(expires))
    elif expires is not None and isinstance(expires, datetime):
        cookie[key]['expires'] = format_date_time(expires.replace(tzinfo=timezone.utc).timestamp())
    if domain is not None:
        cookie[key]['domain'] = domain
    return cookie


def ensure_coroutine(func: Callable) -> Callable:
    if asyncio.iscoroutinefunction(func):
        return func
    else:
        async_func = asyncio.coroutine(func)
        async_func._quart_async_wrapper = True  # type: ignore
        return async_func
