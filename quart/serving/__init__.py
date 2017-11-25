import asyncio
from logging import Logger
from ssl import SSLContext
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Union  # noqa: F401

from .h11 import H11Server
from .h2 import H2Server
from ..wrappers import Request, Response  # noqa: F401

if TYPE_CHECKING:
    from ._base import HTTPProtocol  # noqa
    from ..app import Quart  # noqa


class Server(asyncio.Protocol):
    __slots__ = (
        'access_log_format', 'app', 'logger', 'loop', 'timeout', '_http_server',
    )

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            logger: Optional[Logger],
            access_log_format: str,
            timeout: int,
    ) -> None:
        self.app = app
        self.loop = loop
        self._http_server: Optional['HTTPProtocol'] = None
        self.logger = logger
        self.access_log_format = access_log_format
        self.timeout = timeout

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        ssl_object = transport.get_extra_info('ssl_object')
        if ssl_object is not None:
            protocol = ssl_object.selected_alpn_protocol()
        else:
            protocol = 'http/1.1'

        if protocol == 'h2':
            self._http_server = H2Server(
                self.app, self.loop, transport, self.logger, self.access_log_format,
                self.timeout,
            )
        else:
            self._http_server = H11Server(
                self.app, self.loop, transport, self.logger, self.access_log_format,
                self.timeout,
            )

    def connection_lost(self, exception: Exception) -> None:
        self._http_server.connection_lost(exception)

    def data_received(self, data: bytes) -> None:
        self._http_server.data_received(data)

    def eof_received(self) -> bool:
        return self._http_server.eof_received()


def run_app(
        app: 'Quart',
        *,
        host: str='127.0.0.1',
        port: int=5000,
        access_log_format: str,
        ssl: Optional[SSLContext]=None,
        logger: Optional[Logger]=None,
        timeout: int,
        debug: bool=False,
) -> None:
    """Create a server to run the app on given the options.

    Arguments:
        app: The Quart app to run.
        host: Hostname e.g. localhost
        port: The port to listen on.
        ssl: Optional SSLContext to use.
        logger: Optional logger for serving (access) logs.
    """
    loop = asyncio.get_event_loop()
    loop.set_debug(debug)
    create_server = loop.create_server(
        lambda: Server(app, loop, logger, access_log_format, timeout),
        host, port, ssl=ssl,
    )
    server = loop.run_until_complete(create_server)

    scheme = 'http' if ssl is None else 'https'
    print("Running on {}://{}:{} (CTRL + C to quit)".format(scheme, host, port))

    try:
        loop.run_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
