from base64 import b64encode
from string import ascii_lowercase

import hypothesis.strategies as strategies
from hypothesis import given

from quart.datastructures import CIMultiDict
from quart.wrappers._base import _BaseRequestResponse, BaseRequestWebsocket
from quart.wrappers.request import Request


def test_basic_authorization() -> None:
    headers = CIMultiDict()
    headers['Authorization'] = "Basic {}".format(b64encode(b'identity:secret').decode('ascii'))
    request = BaseRequestWebsocket('GET', 'http', '/', headers)
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
    request = BaseRequestWebsocket('GET', 'http', '/', headers)
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


@given(
    host=strategies.text(alphabet=ascii_lowercase),
    path=strategies.text(alphabet=ascii_lowercase),
)
def test_request_url(host: str, path: str) -> None:
    request = Request('GET', 'http', path, CIMultiDict({'host': host}))
    assert request.url == f"{host}{path}"
