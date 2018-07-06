import os
import time

from quart.datastructures import CIMultiDict
from quart.logging import AccessLogAtoms
from quart.wrappers import Request, Response


def test_access_log_standard_atoms() -> None:
    request_headers = CIMultiDict({
        'Referer': 'stet.io',
        'Remote-Addr': '127.0.0.1',
        'User-Agent': 'quart',
    })
    request = Request('GET', 'http', '/', b'x=y', request_headers)
    response = Response('Hello', 202)
    atoms = AccessLogAtoms(request, response, 'h2', 0.000023)
    assert atoms['h'] == '127.0.0.1'
    assert atoms['l'] == '-'
    assert time.strptime(atoms['t'], '[%d/%b/%Y:%H:%M:%S %z]')
    assert int(atoms['s']) == 202
    assert atoms['m'] == 'GET'
    assert atoms['U'] == '/'
    assert atoms['q'] == 'x=y'
    assert atoms['H'] == 'h2'
    assert int(atoms['b']) == len('Hello')
    assert int(atoms['B']) == len('Hello')
    assert atoms['f'] == 'stet.io'
    assert atoms['a'] == 'quart'
    assert atoms['p'] == f"<{os.getpid()}>"
    assert atoms['not-atom'] == '-'
    assert atoms['T'] == 0
    assert atoms['D'] == 23
    assert atoms['L'] == '0.000023'


def test_access_log_header_atoms() -> None:
    request_headers = CIMultiDict({
        'Random': 'Request',
        'Remote-Addr': '127.0.0.1',
    })
    request = Request('GET', 'http', '/', b'', request_headers)
    response_headers = CIMultiDict({
        'Random': 'Response',
    })
    response = Response('Hello', 200, response_headers)
    atoms = AccessLogAtoms(request, response, 'h2', 0)
    assert atoms['{random}i'] == 'Request'
    assert atoms['{RANDOM}i'] == 'Request'
    assert atoms['{not-atom}i'] == '-'
    assert atoms['{random}o'] == 'Response'
    assert atoms['{RANDOM}o'] == 'Response'


def test_access_log_environ_atoms() -> None:
    os.environ['Random'] = 'Environ'
    request_headers = CIMultiDict({
        'Remote-Addr': '127.0.0.1',
    })
    request = Request('GET', 'http', '/', b'', request_headers)
    response = Response('Hello', 200)
    atoms = AccessLogAtoms(request, response, 'h2', 0)
    assert atoms['{random}e'] == 'Environ'
