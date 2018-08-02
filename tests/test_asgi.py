import pytest

from quart import Quart
from quart.asgi import ASGIHTTPConnection


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'headers, expected',
    [([(b'host', b'quart')], 'quart'), ([], '')],
)
async def test_http_1_0_host_header(headers: list, expected: str) -> None:
    app = Quart(__name__)
    scope = {
        'headers': headers,
        'http_version': '1.0',
        'method': 'GET',
        'scheme': 'https',
        'path': '/',
        'query_string': b'',
    }
    connection = ASGIHTTPConnection(app, scope)
    connection._create_request_from_scope()
    assert connection.request.headers['host'] == expected
