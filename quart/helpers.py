import os
from functools import wraps
from typing import Any, Callable, List, Optional, Tuple, Union
from urllib.parse import quote

from .ctx import _app_ctx_stack, _request_ctx_stack
from .globals import current_app, request, session
from .routing import BuildError
from .signals import message_flashed
from .wrappers import Response

locked_cached_property = property


def get_debug_flag(default: Optional[bool]=None) -> bool:
    value = os.environ.get('QUART_DEBUG')
    if value is None:
        return default
    return value.lower() not in {'0', 'false', 'no'}


async def make_response(*args: Any) -> Response:
    """Create a response, a simple wrapper function.

    This is most useful when you want to alter a Response before
    returning it, for example

    .. code-block:: python

        response = make_response(render_template('index.html'))
        response.headers['X-Header'] = 'Something'

    """
    if not args:
        return current_app.response_class()
    if len(args) == 1:
        args = args[0]

    return await current_app.make_response(args)


async def flash(message: str, category: str='message') -> None:
    """Add a message (with optional category) to the session store.

    This is typically used to flash a message to a user that will be
    stored in the session and shown during some other request. For
    example,

    .. code-block:: python

        @app.route('/login', methods=['POST'])
        async def login():
            ...
            await flash('Login successful')
            return redirect(url_for('index'))

    allows the index route to show the flashed messsages, without
    having to accept the message as an argument or otherwise.  See
    :func:`~quart.helpers.get_flashed_messages` for message retrieval.
    """
    flashes = session.get('_flashes', [])
    flashes.append((category, message))
    session['_flashes'] = flashes
    await message_flashed.send(
        current_app._get_current_object(), message=message, category=category,
    )


def get_flashed_messages(
        with_categories: bool=False,
        category_filter: List[str]=[],
) -> Union[List[str], List[Tuple[str, str]]]:
    """Retrieve the flahshed messages stored in the session.

    This is mostly useful in templates where it is exposed as a global
    function, for example

    .. code-block:: jinja2

        <ul>
        {% for message in get_flashed_messages() %}
          <li>{{ message }}</li>
        {% endfor %}
        </ul>

    Note that caution is required for usage of ``category_filter`` as
    all messages will be popped, but only those matching the filter
    returned. See :func:`~quart.helpers.flash` for message creation.
    """
    flashes = session.pop('_flashes') if '_flashes' in session else []
    if category_filter:
        flashes = [flash for flash in flashes if flash[0] in category_filter]
    if not with_categories:
        flashes = [flash[1] for flash in flashes]
    return flashes


def get_template_attribute(template_name: str, attribute: str) -> Any:
    """Load a attribute from a template.

    This is useful in Python code in order to use attributes in
    templates.

    Arguments:
        template_name: To load the attribute from.
        attribute: The attribute name to load
    """
    return getattr(current_app.jinja_env.get_template(template_name).module, attribute)


def url_for(
        endpoint: str,
        *,
        _anchor: Optional[str]=None,
        _external: Optional[bool]=None,
        _method: Optional[str]=None,
        _scheme: Optional[str]=None,
        **values: Any,
) -> str:
    """Return the url for a specific endpoint.

    This is most useful in templates and redirects to create a URL
    that can be used in the browser.

    Arguments:
        endpoint: The endpoint to build a url for, if prefixed with
            ``.`` it targets endpoint's in the current blueprint.
        _anchor: Additional anchor text to append (i.e. #text).
        _external: Return an absolute url for external (to app) usage.
        _method: The method to consider alongside the endpoint.
        _scheme: A specific scheme to use.
        values: The values to build into the URL, as specified in
            the endpoint rule.
    """
    app_context = _app_ctx_stack.top
    request_context = _request_ctx_stack.top

    if request_context is not None:
        url_adapter = request_context.url_adapter
        if endpoint.startswith('.'):
            if request.blueprint is not None:
                endpoint = request.blueprint + endpoint
            else:
                endpoint = endpoint[1:]
        if _external is None:
            _external = False
    elif app_context is not None:
        url_adapter = app_context.url_adapter
        if _external is None:
            _external = True
    else:
        raise RuntimeError('Cannot create a url outside of an application context')

    if url_adapter is None:
        raise RuntimeError(
            'Unable to create a url adapter, try setting the the SERVER_NAME config variable.'
        )
    if _scheme is not None and not _external:
        raise ValueError('External must be True for scheme usage')

    app_context.app.inject_url_defaults(endpoint, values)
    try:
        url = url_adapter.build(
            endpoint, values, method=_method, scheme=_scheme, external=_external,
        )
    except BuildError as error:
        return app_context.app.handle_url_build_error(error, endpoint, values)

    if _anchor is not None:
        quoted_anchor = quote(_anchor)
        url = f"{url}#{quoted_anchor}"
    return url


def stream_with_context(func: Callable) -> Callable:
    """Share the current request context with a generator.

    This allows the request context to be accessed within a streaming
    generator, for example,

    .. code-block:: python

        @app.route('/')
        def index() -> AsyncGenerator[bytes, None]:
            @stream_with_context
            async def generator() -> bytes:
                yield request.method.encode()
                yield b' '
                yield request.path.encode()

            return generator()

    """
    request_context = _request_ctx_stack.top.copy()

    @wraps(func)
    async def generator(*args: Any, **kwargs: Any) -> Any:
        async with request_context:
            async for data in func(*args, **kwargs):
                yield data
    return generator


def _endpoint_from_view_func(view_func: Callable) -> str:
    return view_func.__name__
