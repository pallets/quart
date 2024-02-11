from __future__ import annotations

import warnings

import pytest
from hypercorn.typing import HTTPScope
from werkzeug.datastructures import Headers

from quart.routing import QuartMap
from quart.testing import no_op_push
from quart.wrappers.request import Request


@pytest.mark.parametrize(
    "server_name, warns",
    [("localhost", False), ("quart.com", True)],
)
async def test_bind_warning(server_name: str, warns: bool, http_scope: HTTPScope) -> None:
    map_ = QuartMap(host_matching=False)
    request = Request(
        "GET",
        "http",
        "/",
        b"",
        Headers([("host", "Localhost")]),
        "",
        "1.1",
        http_scope,
        send_push_promise=no_op_push,
    )

    if warns:
        with pytest.warns(UserWarning):
            map_.bind_to_request(request, subdomain=None, server_name=server_name)
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            map_.bind_to_request(request, subdomain=None, server_name=server_name)
