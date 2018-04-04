import asyncio
import os
import sys
from logging import Logger
from pathlib import Path
from ssl import SSLContext
from types import ModuleType
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING  # noqa: F401

from .h11 import H11Server, H2CProtocolRequired, WebsocketProtocolRequired
from .h2 import H2Server
from .websocket import WebsocketServer
from ..wrappers import Request, Response  # noqa: F401

if TYPE_CHECKING:
    from ._base import HTTPServer  # noqa
    from ..app import Quart  # noqa


class Server(asyncio.Protocol):
    __slots__ = (
        'access_log_format', 'app', 'logger', 'loop', 'keep_alive_timeout', '_http_server',
    )

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            logger: Optional[Logger],
            access_log_format: str,
            keep_alive_timeout: int,
            *,
            h11_max_incomplete_size: Optional[int]=None,
    ) -> None:
        self.app = app
        self.loop = loop
        self._server: Optional['HTTPServer'] = None
        self.logger = logger
        self.access_log_format = access_log_format
        self.keep_alive_timeout = keep_alive_timeout
        self.h11_max_incomplete_size = h11_max_incomplete_size
        self._ssl_enabled = False

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        ssl_object = transport.get_extra_info('ssl_object')
        if ssl_object is not None:
            self._ssl_enabled = True
            protocol = ssl_object.selected_alpn_protocol()
        else:
            protocol = 'http/1.1'

        if protocol == 'h2':
            self._server = H2Server(
                self.app, self.loop, transport, self.logger, self.access_log_format,
                self.keep_alive_timeout,
            )
        else:
            self._server = H11Server(
                self.app, self.loop, transport, self.logger, self.access_log_format,
                self.keep_alive_timeout, max_incomplete_size=self.h11_max_incomplete_size,
            )

    def connection_lost(self, exception: Exception) -> None:
        self._server.connection_lost(exception)

    def data_received(self, data: bytes) -> None:
        try:
            self._server.data_received(data)
        except WebsocketProtocolRequired as error:
            self._server = WebsocketServer(
                self.app, self.loop, self._server.transport, self.logger, error.request,
            )
        except H2CProtocolRequired as error:
            self._server = H2Server(
                self.app, self.loop, self._server.transport, self.logger, self.access_log_format,
                self.keep_alive_timeout, upgrade_request=error.request,
            )

    def eof_received(self) -> bool:
        if self._ssl_enabled:
            # Returning anything other than False has no affect under
            # SSL, and just raises an annoying warning.
            return False
        return self._server.eof_received()

    def pause_writing(self) -> None:
        self._server.pause_writing()

    def resume_writing(self) -> None:
        self._server.resume_writing()


async def _observe_changes() -> bool:
    last_updates: Dict[ModuleType, float] = {}
    while True:
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename is None:
                continue
            mtime = Path(filename).stat().st_mtime
            if mtime > last_updates.get(module, mtime):
                return True
            last_updates[module] = mtime
        await asyncio.sleep(1)


def run_app(
        app: 'Quart',
        *,
        host: str='127.0.0.1',
        port: int=5000,
        access_log_format: str,
        ssl: Optional[SSLContext]=None,
        logger: Optional[Logger]=None,
        keep_alive_timeout: int,
        debug: bool=False,
        use_reloader: bool=False,
        loop: Optional[asyncio.AbstractEventLoop]=None,
) -> None:
    """Create a server to run the app on given the options.

    Arguments:
        app: The Quart app to run.
        host: Hostname e.g. localhost
        port: The port to listen on.
        ssl: Optional SSLContext to use.
        logger: Optional logger for serving (access) logs.
        keep_alive_timeout: Timeout for inactive connections.
        use_reloader: Automatically reload on changes.
        loop: Asyncio loop to create the server in, if None, take default one.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    loop.set_debug(debug)
    create_server = loop.create_server(
        lambda: Server(app, loop, logger, access_log_format, keep_alive_timeout),
        host, port, ssl=ssl,
    )
    server = loop.run_until_complete(create_server)

    scheme = 'http' if ssl is None else 'https'
    print("Running on {}://{}:{} (CTRL + C to quit)".format(scheme, host, port))  # noqa: T001

    try:
        if use_reloader:
            loop.run_until_complete(_observe_changes())
            server.close()
            loop.run_until_complete(server.wait_closed())
            # Restart this process (only safe for dev/debug)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            loop.run_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
