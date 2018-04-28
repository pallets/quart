from typing import Optional, Set

import pytest

from quart.app import Quart


def test_endpoint_overwrite() -> None:
    app = Quart(__name__)

    def route() -> str:
        return ''

    app.add_url_rule('/', 'index', route, ['GET'])
    with pytest.raises(AssertionError):
        app.add_url_rule('/a', 'index', route, ['GET'])


@pytest.mark.parametrize(
    'methods, required_methods, automatic_options',
    [
        ({}, {}, False),
        ({}, {}, True),
        ({'GET', 'PUT'}, {}, False),
        ({'GET', 'PUT'}, {}, True),
        ({}, {'GET', 'PUT'}, False),
        ({}, {'GET', 'PUT'}, True),
    ],
)
def test_add_url_rule_methods(
        methods: Set[str], required_methods: Set[str], automatic_options: bool,
) -> None:
    app = Quart(__name__)

    def route() -> str:
        return ''

    route.methods = methods  # type: ignore
    route.required_methods = required_methods  # type: ignore

    non_func_methods = {'PATCH'} if not methods else None
    app.add_url_rule(
        '/', 'end', route, non_func_methods, provide_automatic_options=automatic_options,
    )
    result = {'PATCH'} if not methods else set()
    if automatic_options:
        result.add('OPTIONS')
    result.update(methods)
    result.update(required_methods)
    if 'GET' in result:
        result.add('HEAD')
    assert app.url_map.endpoints['end'][0].methods == result


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
        app.add_url_rule('/', view_func=route, subdomain=subdomain, host=host)
