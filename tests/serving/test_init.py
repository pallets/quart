from unittest.mock import Mock

from quart.serving import Server
from quart.serving.h11 import H11Server
from quart.serving.h2 import H2Server


def test_server() -> None:
    h2_ssl_mock = Mock()
    h2_ssl_mock.selected_alpn_protocol.return_value = 'h2'
    transport = Mock()
    transport.get_extra_info.return_value = h2_ssl_mock
    server = Server(Mock(), Mock(), Mock(), '', 5)
    server.connection_made(transport)
    assert isinstance(server._server, H2Server)
    transport.get_extra_info.return_value = None
    server.connection_made(transport)
    assert isinstance(server._server, H11Server)
