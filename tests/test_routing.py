from __future__ import annotations

import pytest
from hypercorn.typing import HTTPScope
from werkzeug.datastructures import Headers

from quart.routing import QuartMap
from quart.testing import no_op_push
from quart.wrappers.request import Request


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "server_name, expected",
    [("localhost", 0), ("quart.com", 1)],
)
async def test_bind_warning(server_name: str, expected: int, http_scope: HTTPScope) -> None:
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
    with pytest.warns(None) as record:
        map_.bind_to_request(request, subdomain=None, server_name=server_name)

    assert len(record) == expected
