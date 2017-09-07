import asyncio
from unittest.mock import Mock

import h11
import h2

from quart.serving import H11Server, H2Server, Server
from quart.wrappers import CIMultiDict

BASIC_H11_HEADERS = [('Host', 'quart')]
BASIC_H2_HEADERS = [
    (':authority', 'quart'), (':path', '/'), (':scheme', 'https'), (':method', 'GET'),
]


def test_server() -> None:
    h2_ssl_mock = Mock()
    h2_ssl_mock.selected_alpn_protocol.return_value = 'h2'
    transport = Mock()
    transport.get_extra_info.return_value = h2_ssl_mock
    server = Server(Mock(), Mock())
    server.connection_made(transport)
    assert isinstance(server._http_server, H2Server)
    transport.get_extra_info.return_value = None
    server.connection_made(transport)
    assert isinstance(server._http_server, H11Server)


def test_h11server(event_loop: asyncio.AbstractEventLoop) -> None:
    server = H11Server(Mock(), event_loop, Mock())
    server.handle_request = Mock()  # type: ignore
    connection = h11.Connection(h11.CLIENT)
    server.data_received(
        connection.send(h11.Request(method='GET', target='/', headers=BASIC_H11_HEADERS)),
    )
    server.data_received(connection.send(h11.EndOfMessage()))
    server.handle_request.assert_called_once_with(0, 'GET', '/', CIMultiDict(BASIC_H11_HEADERS))


def test_h2server(event_loop: asyncio.AbstractEventLoop) -> None:
    server = H2Server(Mock(), event_loop, Mock())
    server.handle_request = Mock()  # type: ignore
    connection = h2.connection.H2Connection()
    connection.initiate_connection()
    server.data_received(connection.data_to_send())
    connection.send_headers(1, BASIC_H2_HEADERS, end_stream=True)
    server.data_received(connection.data_to_send())
    server.handle_request.assert_called_once_with(1, 'GET', '/', CIMultiDict(BASIC_H2_HEADERS))
