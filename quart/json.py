import json
from typing import Any

from .globals import current_app
from .wrappers import Response


def jsonify(*args: Any, **kwargs: Any) -> Response:
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

    body = json.dumps(data, indent=indent, separators=separators)
    return Response(body, content_type=current_app.config['JSONIFY_MIMETYPE'])
