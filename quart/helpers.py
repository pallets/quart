from typing import Any, List, Optional, Tuple, Union
from urllib.parse import quote

from .ctx import _app_ctx_stack, _request_ctx_stack
from .globals import current_app, request, session
from .signals import message_flashed
from .wrappers import Response


def make_response(*args: Any) -> Response:
    if not args:
        return current_app.response_class()
    if len(args) == 1:
        return current_app.make_response(args[0])
    else:
        return current_app.make_response(args)


def flash(message: str, category: str='message') -> None:
    flashes = session.get('_flashes', [])
    flashes.append((category, message))
    session['_flashes'] = flashes
    message_flashed.send(current_app._get_current_object(), message=message, category=category)


def get_flashed_messages(
        with_categories: bool=False,
        category_filter: List[str]=[],
) -> Union[List[str], List[Tuple[str, str]]]:
    flashes = session.pop('_flashes') if '_flashes' in session else []
    if category_filter:
        flashes = [flash for flash in flashes if flash[0] in category_filter]
    if not category_filter:
        flashes = [flash[1] for flash in flashes]
    return flashes


def url_for(
        endpoint: str,
        *,
        _anchor: Optional[str]=None,
        _method: Optional[str]=None,
        _scheme: Optional[str]=None,
        **values: Any
) -> str:
    app_context = _app_ctx_stack.top
    request_context = _request_ctx_stack.top

    if request_context is not None:
        url_adapter = request_context.url_adapter
        if endpoint.startswith('.'):
            if request.blueprint is not None:
                endpoint = request.blueprint + endpoint
            else:
                endpoint = endpoint[1:]
    elif app_context is not None:
        url_adapter = app_context.url_adapter
    else:
        raise RuntimeError('Cannot create a url outside of an application context')

    if url_adapter is None:
        raise RuntimeError(
            'Unable to create a url adapter, try setting the the SERVER_NAME config variable.'
        )

    url = url_adapter.build(endpoint, values, method=_method, scheme=_scheme)
    if _anchor is not None:
        quoted_anchor = quote(_anchor)
        url = f"{url}#{quoted_anchor}"
    return url
