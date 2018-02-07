from typing import Optional

import pytest

from quart.app import Quart


def test_endpoint_overwrite() -> None:
    app = Quart(__name__)

    def route() -> str:
        return ''

    app.add_url_rule('/', route, ['GET'], 'index')
    with pytest.raises(AssertionError):
        app.add_url_rule('/a', route, ['GET'], 'index')


@pytest.mark.asyncio
async def test_host_matching() -> None:
    app = Quart(__name__, static_host='quart.com', host_matching=True)
    app.config['SERVER_NAME'] = 'quart.com'

    @app.route('/')
    def route() -> str:
        return ''

    test_client = app.test_client()
    response = await test_client.get('/', headers={'host': 'quart.com'})
    assert response.status_code == 200

    response = await test_client.get('/', headers={'host': 'localhost'})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_subdomain() -> None:
    app = Quart(__name__, static_host='quart.com', host_matching=True)
    app.config['SERVER_NAME'] = 'quart.com'

    @app.route('/', subdomain='<subdomain>')
    def route(subdomain: str) -> str:
        return subdomain

    test_client = app.test_client()
    response = await test_client.get('/', headers={'host': 'sub.quart.com'})
    assert (await response.get_data(raw=False)) == 'sub'


@pytest.mark.parametrize(
    'host_matching, server_name, subdomain, host, error',
    [
        (False, None, 'foo', None, RuntimeError),
        (False, None, None, 'foo', RuntimeError),
        (True, None, 'foo', 'foo', ValueError),
        (True, None, 'foo', None, RuntimeError),
        (True, None, None, None, RuntimeError),
    ],
    ids=[
        'No host matching with subdomain',
        'No host matching with host',
        'Host and subdomain',
        'No server name with subdomain',
        'No host and no server name with host matching',
    ],
)
def test_add_url_rule_host_and_subdomain_errors(
        host_matching: bool, server_name: Optional[str], subdomain: Optional[str],
        host: Optional[str], error: Exception,
) -> None:
    static_host = 'quart.com' if host_matching else None
    app = Quart(__name__, static_host=static_host, host_matching=host_matching)
    app.config['SERVER_NAME'] = server_name

    def route() -> str:
        return ''

    with pytest.raises(error):
        app.add_url_rule('/', route, subdomain=subdomain, host=host)
