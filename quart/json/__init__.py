import json
from datetime import date
from email.utils import formatdate
from time import mktime
from typing import Any, TYPE_CHECKING
from uuid import UUID

from jinja2 import Markup

from ..globals import _app_ctx_stack, _request_ctx_stack, current_app, request

if TYPE_CHECKING:
    from ..wrappers import Response  # noqa: F401


def dumps(object_: Any, **kwargs: Any) -> str:
    json_encoder = JSONEncoder
    if _app_ctx_stack.top is not None:  # has_app_context requires a circular import
        json_encoder = current_app.json_encoder
        if _request_ctx_stack.top is not None:  # has_request_context requires a circular import
            blueprint = current_app.blueprints.get(request.blueprint)
            if blueprint is not None and blueprint.json_encoder is not None:
                json_encoder = blueprint.json_encoder
        kwargs.setdefault('ensure_ascii', current_app.config['JSON_AS_ASCII'])
        kwargs.setdefault('sort_keys', current_app.config['JSON_SORT_KEYS'])
    kwargs.setdefault('sort_keys', True)
    kwargs.setdefault('cls', json_encoder)

    return json.dumps(object_, **kwargs)


def loads(object_: Any, **kwargs: Any) -> str:
    json_decoder = JSONDecoder
    if _app_ctx_stack.top is not None:  # has_app_context requires a circular import
        json_decoder = current_app.json_decoder
        if _request_ctx_stack.top is not None:  # has_request_context requires a circular import
            blueprint = current_app.blueprints.get(request.blueprint)
            if blueprint is not None and blueprint.json_decoder is not None:
                json_decoder = blueprint.json_decoder
    kwargs.setdefault('cls', json_decoder)

    return json.loads(object_, **kwargs)


def htmlsafe_dumps(object_: Any, **kwargs: Any) -> str:
    # Note in the below the ascii characters are replaced with a
    # unicode similar version.
    result = dumps(object_, **kwargs).replace('<', '<').replace('>', '>')
    return result.replace('&', '&').replace("'", "'")


def tojson_filter(object_: Any, **kwargs: Any) -> Markup:
    return Markup(htmlsafe_dumps(object_, **kwargs))


def jsonify(*args: Any, **kwargs: Any) -> 'Response':
    if args and kwargs:
        raise TypeError('jsonify() behavior undefined when passed both args and kwargs')
    elif len(args) == 1:
        data = args[0]
    else:
        data = args or kwargs

    indent = None
    separators = (',', ':')
    if current_app.config['JSONIFY_PRETTYPRINT_REGULAR'] or current_app.debug:
        indent = 2
        separators = (', ', ': ')

    body = dumps(data, indent=indent, separators=separators)
    return current_app.response_class(body, content_type=current_app.config['JSONIFY_MIMETYPE'])


class JSONEncoder(json.JSONEncoder):

    def default(self, object_: Any) -> Any:
        if isinstance(object_, date):
            return formatdate(timeval=mktime((object_.timetuple())), localtime=False, usegmt=True)
        if isinstance(object_, UUID):
            return str(object_)
        if hasattr(object_, '__html__'):
            return str(object_.__html__())
        return super().default(object_)


class JSONDecoder(json.JSONDecoder):
    pass
