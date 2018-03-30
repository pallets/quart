import asyncio
from email.utils import formatdate
from functools import partial
from logging import Logger
from ssl import SSLObject, SSLSocket
from time import time
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Union  # noqa: F401

from ..datastructures import CIMultiDict
from ..logging import AccessLogAtoms
from ..wrappers import Request, Response  # noqa: F401

if TYPE_CHECKING:
    from ..app import Quart  # noqa


class HTTPServer:

    def __init__(
            self,
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            logger: Optional[Logger],
            protocol: str,
    ) -> None:
        self.loop = loop
        self.transport = transport
        self.logger = logger
        self.protocol = protocol

        self._can_write = asyncio.Event(loop=loop)
        self._can_write.set()

    def data_received(self, data: bytes) -> None:
        # Called whenever data is received.
        pass

    def eof_received(self) -> bool:
        # Either received once or not at all, if the client signals
        # the connection is closed from their side. Is not called for
        # SSL connections. If it returns Falsey the connection is
        # closed from our side.
        return True

    def pause_writing(self) -> None:
        # Will be called whenever the transport crosses the high-water
        # mark.
        self._can_write.clear()

    def resume_writing(self) -> None:
        # Will be called whenever the transport drops back below the
        # low-water mark.
        self._can_write.set()

    def connection_lost(self, _: Exception) -> None:
        # Called once when the connection is closed from our side.
        self.close()

    async def drain(self) -> None:
        await self._can_write.wait()

    def write(self, data: bytes) -> None:
        self.transport.write(data)  # type: ignore

    def close(self) -> None:
        self.transport.close()

    def response_headers(self) -> List[Tuple[str, str]]:
        return [
            ('date', formatdate(time(), usegmt=True)), ('server', f"quart-{self.protocol}"),
        ]

    def cleanup_task(self, future: asyncio.Future) -> None:
        """Call after a task (future) to clean up.

        This should be added as a add_done_callback for any protocol
        task to ensure that the proper cleanup is handled on
        cancellation i.e. early connection closing.
        """
        # Fetch the exception (if exists) from the future, without
        # this asyncio will print annoying warnings.
        try:
            exception = future.exception()
        except Exception as error:
            exception = error
        # If the connection was closed, the exception will be a
        # CancelledError and does not need to be logged (expected
        # behaviour).
        if (
                exception is not None and not isinstance(exception, asyncio.CancelledError) and
                self.logger is not None
        ):
            self.logger.error('Exception handling the request', exc_info=exception)

    @property
    def remote_addr(self) -> str:
        return self.transport.get_extra_info('peername')[0]

    @property
    def ssl_info(self) -> Optional[Union[SSLObject, SSLSocket]]:
        return self.transport.get_extra_info('ssl_object')


class Stream:
    __slots__ = ('buffer', 'request', 'task')

    def __init__(self, loop: asyncio.AbstractEventLoop, request: Request) -> None:
        self.request = request
        self.task: Optional[asyncio.Future] = None

    def append(self, data: bytes) -> None:
        self.request.body.append(data)

    def complete(self) -> None:
        self.request.body.set_complete()


class RequestResponseServer(HTTPServer):

    stream_class = Stream

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            logger: Optional[Logger],
            protocol: str,
            access_log_format: str,
            keep_alive_timeout: float,
    ) -> None:
        super().__init__(loop, transport, logger, protocol)
        self.app = app
        self.streams: Dict[int, Stream] = {}
        self.access_log_format = access_log_format
        self._keep_alive_timeout = keep_alive_timeout
        self._last_activity = time()
        self._keep_alive_timeout_handle = self.loop.call_later(
            self._keep_alive_timeout, self._handle_keep_alive_timeout,
        )

    def write(self, data: bytes) -> None:
        self._last_activity = time()
        super().write(data)

    def close(self) -> None:
        for stream in self.streams.values():
            stream.task.cancel()
        super().close()
        self._keep_alive_timeout_handle.cancel()

    def data_received(self, data: bytes) -> None:
        self._last_activity = time()

    def eof_received(self) -> bool:
        return True

    def handle_request(
            self,
            stream_id: int,
            method: str,
            path: str,
            headers: CIMultiDict,
    ) -> None:
        self._keep_alive_timeout_handle.cancel()
        headers['Remote-Addr'] = self.remote_addr
        scheme = 'https' if self.ssl_info is not None else 'http'
        request = self.app.request_class(
            method, scheme, path, headers,
            max_content_length=self.app.config['MAX_CONTENT_LENGTH'],
            body_timeout=self.app.config['BODY_TIMEOUT'],
        )
        self.streams[stream_id] = self.stream_class(self.loop, request)
        # It is important that the app handles the request in a unique
        # task as the globals are task locals
        self.streams[stream_id].task = asyncio.ensure_future(self._handle_request(stream_id))
        self.streams[stream_id].task.add_done_callback(partial(self._after_request, stream_id))

    async def _handle_request(self, stream_id: int) -> None:
        request = self.streams[stream_id].request
        start_time = time()
        response = await self.app.handle_request(request)
        suppress_body_ = suppress_body(request.method, response.status_code)
        try:
            await asyncio.wait_for(
                self.send_response(stream_id, response, suppress_body_),
                timeout=response.timeout,
            )
        except asyncio.TimeoutError:
            self.close()
        else:
            if self.logger is not None:
                self.logger.info(
                    self.access_log_format,
                    AccessLogAtoms(request, response, self.protocol, time() - start_time),
                )

    async def send_response(self, stream_id: int, response: Response, suppress_body: bool) -> None:
        raise NotImplemented()

    def _after_request(self, stream_id: int, future: asyncio.Future) -> None:
        del self.streams[stream_id]
        if not self.streams:
            self._keep_alive_timeout_handle = self.loop.call_later(
                self._keep_alive_timeout, self._handle_keep_alive_timeout,
            )
        self.cleanup_task(future)

    def _handle_keep_alive_timeout(self) -> None:
        if time() - self._last_activity > self._keep_alive_timeout:
            self.close()


def suppress_body(method: str, status_code: int) -> bool:
    return method == 'HEAD' or 100 <= status_code < 200 or status_code in {204, 304, 412}
