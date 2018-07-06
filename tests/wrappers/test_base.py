from base64 import b64encode

import pytest

from quart.datastructures import CIMultiDict
from quart.wrappers._base import _BaseRequestResponse, BaseRequestWebsocket


def test_basic_authorization() -> None:
    headers = CIMultiDict()
    headers['Authorization'] = "Basic {}".format(b64encode(b'identity:secret').decode('ascii'))
    request = BaseRequestWebsocket('GET', 'http', '/', b'', headers)
    auth = request.authorization
    assert auth.username == 'identity'
    assert auth.password == 'secret'


def test_digest_authorization() -> None:
    headers = CIMultiDict()
    headers['Authorization'] = (
        'Digest '
        'username="identity", '
        'realm="realm@rea.lm", '
        'nonce="abcd1234", '
        'uri="/path", '
        'response="abcd1235", '
        'opaque="abcd1236"'
    )
    request = BaseRequestWebsocket('GET', 'http', '/', b'', headers)
    auth = request.authorization
    assert auth.username == 'identity'
    assert auth.realm == 'realm@rea.lm'
    assert auth.nonce == 'abcd1234'
    assert auth.uri == '/path'
    assert auth.response == 'abcd1235'
    assert auth.opaque == 'abcd1236'


def test_mimetype_get_property() -> None:
    base_request_response = _BaseRequestResponse({'Content-Type': 'text/html; charset=utf-8'})
    assert base_request_response.mimetype == 'text/html'
    assert base_request_response.mimetype_params == {'charset': 'utf-8'}


def test_mimetype_set_property() -> None:
    base_request_response = _BaseRequestResponse(None)
    base_request_response.mimetype = 'text/html'
    assert base_request_response.headers['Content-Type'] == 'text/html; charset=utf-8'
    base_request_response.mimetype = 'application/json'
    assert base_request_response.headers['Content-Type'] == 'application/json'


@pytest.mark.parametrize(
    'method, scheme, host, path, query_string,'
    'expected_path, expected_full_path, expected_url, expected_base_url,'
    'expected_url_root, expected_host_url',
    [
        (
            'GET', 'http', 'quart.com', '/', b'',
            '/', '/', 'http://quart.com/', 'http://quart.com/', 'http://quart.com/',
            'http://quart.com',
        ),
        (
            'GET', 'http', 'quart.com', '/', b'a=b',
            '/', '/?a=b', 'http://quart.com/?a=b', 'http://quart.com/', 'http://quart.com/',
            'http://quart.com',
        ),
        (
            'GET', 'https', 'quart.com', '/branch/leaf', b'a=b',
            '/branch/leaf', '/branch/leaf?a=b', 'https://quart.com/branch/leaf?a=b',
            'https://quart.com/branch/leaf', 'https://quart.com/branch/', 'https://quart.com',
        ),
    ],
)
def test_url_structure(
        method: str, scheme: str, host: str, path: str, query_string: bytes,
        expected_path: str, expected_full_path: str, expected_url: str,
        expected_base_url: str, expected_url_root: str, expected_host_url: str,
) -> None:
    base_request_websocket = BaseRequestWebsocket(
        method, scheme, path, query_string, CIMultiDict({'host': host}),
    )

    assert base_request_websocket.path == expected_path
    assert base_request_websocket.query_string == query_string
    assert base_request_websocket.full_path == expected_full_path
    assert base_request_websocket.url == expected_url
    assert base_request_websocket.base_url == expected_base_url
    assert base_request_websocket.url_root == expected_url_root
    assert base_request_websocket.host_url == expected_host_url
    assert base_request_websocket.host == host
    assert base_request_websocket.method == method
    assert base_request_websocket.scheme == scheme
    assert base_request_websocket.is_secure == scheme.endswith('s')


def test_query_string() -> None:
    base_request_websocket = BaseRequestWebsocket(
        'GET', 'http', '/', b'a=b&a=c&f', CIMultiDict({'host': 'localhost'}),
    )
    assert base_request_websocket.query_string == b'a=b&a=c&f'
    assert base_request_websocket.args.getlist('a') == ['b', 'c']
    assert base_request_websocket.args['f'] == ''
