from __future__ import annotations

import mimetypes
import os
import pkgutil
import sys
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, cast, Iterable, NoReturn
from zlib import adler32

from flask.helpers import get_root_path as get_root_path  # noqa: F401
from werkzeug.exceptions import abort as werkzeug_abort, NotFound
from werkzeug.utils import redirect as werkzeug_redirect, safe_join
from werkzeug.wrappers import Response as WerkzeugResponse

from .globals import _cv_request, current_app, request, request_ctx, session
from .signals import message_flashed
from .typing import FilePath, ResponseReturnValue, ResponseTypes
from .utils import file_path_to_path
from .wrappers import Response
from .wrappers.response import ResponseBody

DEFAULT_MIMETYPE = "application/octet-stream"

locked_cached_property = property


def get_debug_flag() -> bool:
    """Reads QUART_DEBUG environment variable to determine whether to run
    the app in debug mode. If unset, and development mode has been
    configured, it will be enabled automatically.
    """
    value = os.getenv("QUART_DEBUG", None)
    return bool(value and value.lower() not in {"0", "false", "no"})


def get_load_dotenv(default: bool = True) -> bool:
    """Get whether the user has disabled loading default dotenv files by
    setting :envvar:`QUART_SKIP_DOTENV`. The default is ``True``, load
    the files.
    :param default: What to return if the env var isn't set.
    """
    val = os.environ.get("QUART_SKIP_DOTENV")

    if not val:
        return default

    return val.lower() in ("0", "false", "no")


async def make_response(*args: Any) -> ResponseTypes:
    """Create a response, a simple wrapper function.

    This is most useful when you want to alter a Response before
    returning it, for example

    .. code-block:: python

        response = make_response(render_template('index.html'))
        response.headers['X-Header'] = 'Something'

    """
    if not args:
        return current_app.response_class("")
    if len(args) == 1:
        args = args[0]

    return await current_app.make_response(cast(ResponseReturnValue, args))


async def make_push_promise(path: str) -> None:
    """Create a push promise, a simple wrapper function.

    This takes a path that should be pushed to the client if the
    protocol is HTTP/2.

    """
    return await request.send_push_promise(path)


async def flash(message: str, category: str = "message") -> None:
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

    allows the index route to show the flashed messages, without
    having to accept the message as an argument or otherwise.  See
    :func:`~quart.helpers.get_flashed_messages` for message retrieval.
    """
    flashes = session.get("_flashes", [])
    flashes.append((category, message))
    session["_flashes"] = flashes
    app = current_app._get_current_object()  # type: ignore
    await message_flashed.send_async(
        app, _sync_wrapper=app.ensure_async, message=message, category=category
    )


def get_flashed_messages(
    with_categories: bool = False, category_filter: Iterable[str] = ()
) -> list[str] | list[tuple[str, str]]:
    """Retrieve the flashed messages stored in the session.

    This is mostly useful in templates where it is exposed as a global
    function, for example

    .. code-block:: html+jinja

        <ul>
        {% for message in get_flashed_messages() %}
          <li>{{ message }}</li>
        {% endfor %}
        </ul>

    Note that caution is required for usage of ``category_filter`` as
    all messages will be popped, but only those matching the filter
    returned. See :func:`~quart.helpers.flash` for message creation.
    """
    flashes = request_ctx.flashes
    if flashes is None:
        flashes = session.pop("_flashes") if "_flashes" in session else []
        request_ctx.flashes = flashes
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
    _anchor: str | None = None,
    _external: bool | None = None,
    _method: str | None = None,
    _scheme: str | None = None,
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
    return current_app.url_for(
        endpoint,
        _anchor=_anchor,
        _method=_method,
        _scheme=_scheme,
        _external=_external,
        **values,
    )


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
    request_context = _cv_request.get().copy()

    @wraps(func)
    async def generator(*args: Any, **kwargs: Any) -> Any:
        async with request_context:
            async for data in func(*args, **kwargs):
                yield data

    return generator


def find_package(name: str) -> tuple[Path | None, Path]:
    """Finds packages install prefix (or None) and it's containing Folder"""
    module = name.split(".")[0]
    loader = pkgutil.get_loader(module)
    if name == "__main__" or loader is None:
        package_path = Path.cwd()
    else:
        if hasattr(loader, "get_filename"):
            filename = loader.get_filename(module)
        else:
            __import__(name)
            filename = sys.modules[name].__file__
        package_path = Path(filename).resolve().parent
        if hasattr(loader, "is_package"):
            is_package = loader.is_package(module)
            if is_package:
                package_path = Path(package_path).resolve().parent
    sys_prefix = Path(sys.prefix).resolve()
    try:
        package_path.relative_to(sys_prefix)
    except ValueError:
        return None, package_path
    else:
        return sys_prefix, package_path


async def send_from_directory(
    directory: FilePath,
    file_name: str,
    *,
    mimetype: str | None = None,
    as_attachment: bool = False,
    attachment_filename: str | None = None,
    add_etags: bool = True,
    cache_timeout: int | None = None,
    conditional: bool = True,
    last_modified: datetime | None = None,
) -> Response:
    """Send a file from a given directory.

    Arguments:
       directory: Directory that when combined with file_name gives
           the file path.
       file_name: File name that when combined with directory gives
           the file path.

    See :func:`send_file` for the other arguments.
    """
    raw_file_path = safe_join(str(directory), file_name)
    if raw_file_path is None:
        raise NotFound()
    file_path = Path(raw_file_path)
    if not file_path.is_file():
        raise NotFound()
    return await send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=as_attachment,
        attachment_filename=attachment_filename,
        add_etags=add_etags,
        cache_timeout=cache_timeout,
        conditional=conditional,
        last_modified=last_modified,
    )


async def send_file(
    filename_or_io: FilePath | BytesIO,
    mimetype: str | None = None,
    as_attachment: bool = False,
    attachment_filename: str | None = None,
    add_etags: bool = True,
    cache_timeout: int | None = None,
    conditional: bool = False,
    last_modified: datetime | None = None,
) -> Response:
    """Return a Response to send the filename given.

    Arguments:
        filename_or_io: The filename (path) to send, remember to use
            :func:`safe_join`.
        mimetype: Mimetype to use, by default it will be guessed or
            revert to the DEFAULT_MIMETYPE.
        as_attachment: If true use the attachment filename in a
            Content-Disposition attachment header.
        attachment_filename: Name for the filename, if it differs
        add_etags: Set etags based on the filename, size and
            modification time.
        last_modified: Used to override the last modified value.
        cache_timeout: Time in seconds for the response to be cached.

    """
    file_body: ResponseBody
    file_size: int | None = None
    etag: str | None = None
    if isinstance(filename_or_io, BytesIO):
        file_body = current_app.response_class.io_body_class(filename_or_io)
        file_size = filename_or_io.getbuffer().nbytes
    else:
        file_path = file_path_to_path(filename_or_io)
        file_size = file_path.stat().st_size
        if attachment_filename is None:
            attachment_filename = file_path.name
        file_body = current_app.response_class.file_body_class(file_path)
        if last_modified is None:
            last_modified = file_path.stat().st_mtime  # type: ignore
        if cache_timeout is None:
            cache_timeout = current_app.get_send_file_max_age(str(file_path))
        etag = "{}-{}-{}".format(
            file_path.stat().st_mtime, file_path.stat().st_size, adler32(bytes(file_path))
        )

    if mimetype is None and attachment_filename is not None:
        mimetype = mimetypes.guess_type(attachment_filename)[0] or DEFAULT_MIMETYPE
    if mimetype is None:
        raise ValueError(
            "The mime type cannot be inferred, please set it manually via the mimetype argument."
        )

    response = current_app.response_class(file_body, mimetype=mimetype)
    response.content_length = file_size

    if as_attachment:
        response.headers.add("Content-Disposition", "attachment", filename=attachment_filename)

    if last_modified is not None:
        response.last_modified = last_modified

    response.cache_control.public = True
    if cache_timeout is not None:
        response.cache_control.max_age = cache_timeout
        response.expires = datetime.utcnow() + timedelta(seconds=cache_timeout)

    if add_etags and etag is not None:
        response.set_etag(etag)

    if conditional:
        await response.make_conditional(request, accept_ranges=True, complete_length=file_size)
    return response


@lru_cache(maxsize=None)
def _split_blueprint_path(name: str) -> list[str]:
    bps = [name]
    while "." in bps[-1]:
        bps.append(bps[-1].rpartition(".")[0])
    return bps


def abort(code: int | Response, *args: Any, **kwargs: Any) -> NoReturn:
    """Raise an HTTPException for the given status code."""
    if current_app:
        current_app.aborter(code, *args, **kwargs)

    werkzeug_abort(code, *args, **kwargs)


def redirect(location: str, code: int = 302) -> WerkzeugResponse:
    """Redirect to the location with the status code."""
    if current_app:
        return current_app.redirect(location, code=code)

    return werkzeug_redirect(location, code=code)
