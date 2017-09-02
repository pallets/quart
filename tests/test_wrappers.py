from asyncio import Future
from base64 import b64encode

from quart.datastructures import CIMultiDict
from quart.wrappers import Request


def test_basic_authorization() -> None:
    headers = CIMultiDict()
    headers['Authorization'] = "Basic {}".format(b64encode(b'identity:secret').decode('ascii'))
    request = Request('GET', '/', headers, Future())
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
    request = Request('GET', '/', headers, Future())
    auth = request.authorization
    assert auth.username == 'identity'
    assert auth.realm == 'realm@rea.lm'
    assert auth.nonce == 'abcd1234'
    assert auth.uri == '/path'
    assert auth.response == 'abcd1235'
    assert auth.opaque == 'abcd1236'
