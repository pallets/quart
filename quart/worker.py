import asyncio
import os
import warnings
from asyncio.base_events import Server as AIOServer  # noqa: F401
from ssl import SSLContext
from typing import Any, List, Optional  # noqa: F401

from gunicorn.workers.base import Worker
from hypercorn import Config
from hypercorn.run import Server


class GunicornWorker(Worker):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            'Gunicorn is deprecated, please use an ASGI server. Hypercorn is recommended',
            DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.servers: List[AIOServer] = []

    def init_process(self) -> None:
        asyncio.get_event_loop().close()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        super().init_process()

    def run(self) -> None:
        create_server = asyncio.ensure_future(self._run(), loop=self.loop)  # type: ignore

        try:
            self.loop.run_until_complete(create_server)

            self.loop.run_until_complete(self._check_alive())
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    async def _run(self) -> None:
        ssl_context = self._create_ssl_context()
        config = Config()
        if self.cfg.accesslog:
            config.access_logger = self.log.access_log
        config.access_log_format = self.cfg.access_log_format
        if self.cfg.errorlog:
            config.error_logger = self.log.error_log
        config.keep_alive_timeout = self.cfg.keepalive
        max_fields_size = self.cfg.limit_request_fields * self.cfg.limit_request_field_size
        config.h11_max_incomplete_size = self.cfg.limit_request_line + max_fields_size
        for sock in self.sockets:
            server = await self.loop.create_server(
                lambda: Server(self.wsgi, self.loop, config),
                sock=sock.sock, ssl=ssl_context,
            )
            self.servers.append(server)

    async def _check_alive(self) -> None:
        # If our parent changed then we shut down.
        pid = os.getpid()
        try:
            while self.alive:  # type: ignore
                self.notify()

                if pid == os.getpid() and self.ppid != os.getppid():
                    self.alive = False
                    self.log.info("Parent changed, shutting down: %s", self)
                else:
                    await asyncio.sleep(1.0, loop=self.loop)
        except (Exception, BaseException, GeneratorExit, KeyboardInterrupt):
            pass

        await self.close()

    def _create_ssl_context(self) -> Optional[SSLContext]:
        ssl_context = None
        if self.cfg.is_ssl:
            ssl_context = SSLContext(self.cfg.ssl_version)
            ssl_context.load_cert_chain(self.cfg.certfile, self.cfg.keyfile)
            if self.cfg.ca_certs:
                ssl_context.load_verify_locations(self.cfg.ca_certs)
            if self.cfg.ciphers:
                ssl_context.set_ciphers(self.cfg.ciphers)
            ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
        return ssl_context

    async def close(self) -> None:
        for server in self.servers:
            server.close()
            await server.wait_closed()


class GunicornUVLoopWorker(GunicornWorker):

    def init_process(self) -> None:
        import uvloop

        asyncio.get_event_loop().close()
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        super().init_process()
