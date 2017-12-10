import asyncio
from datetime import datetime
from email.utils import formatdate
from functools import partial
from logging import Logger
from time import time
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Union  # noqa: F401

from ..datastructures import CIMultiDict
from ..logging import AccessLogAtoms
from ..wrappers import Request, Response  # noqa: F401

if TYPE_CHECKING:
    from ..app import Quart  # noqa


class Stream:
    __slots__ = ('buffer', 'request', 'task')

    def __init__(self, loop: asyncio.AbstractEventLoop, request: Request) -> None:
        self.request = request
        self.task: Optional[asyncio.Future] = None

    def append(self, data: bytes) -> None:
        self.request.body.append(data)

    def complete(self) -> None:
        self.request.body.set_complete()


class HTTPProtocol:

    protocol = ''
    stream_class = Stream

    def __init__(
            self,
            app: 'Quart',
            loop: asyncio.AbstractEventLoop,
            transport: asyncio.BaseTransport,
            logger: Optional[Logger],
            access_log_format: str,
            timeout: int,
    ) -> None:
        self.app = app
        self.loop = loop
        self.logger = logger
        self.streams: Dict[int, Stream] = {}
        self.access_log_format = access_log_format
        self._timeout = timeout
        self._last_activity = time()
        self._timeout_handle = self.loop.call_later(self._timeout, self._handle_timeout)
        self._transport = transport

    def connection_lost(self, _: Exception) -> None:
        self.close()

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
        self._timeout_handle.cancel()
        headers['Remote-Addr'] = self._transport.get_extra_info('peername')[0]
        request = self.app.request_class(method, path, headers)
        self.streams[stream_id] = self.stream_class(self.loop, request)
        # It is important that the app handles the request in a unique
        # task as the globals are task locals
        self.streams[stream_id].task = asyncio.ensure_future(self._handle_request(stream_id))
        self.streams[stream_id].task.add_done_callback(partial(self._after_request, stream_id))

    async def _handle_request(self, stream_id: int) -> None:
        request = self.streams[stream_id].request
        start_time = datetime.now()
        response = await self.app.handle_request(request)
        await self.send_response(stream_id, response)
        if self.logger is not None:
            self.logger.info(
                self.access_log_format,
                AccessLogAtoms(request, response, self.protocol, datetime.now() - start_time),
            )

    async def send_response(self, stream_id: int, response: Response) -> None:
        raise NotImplemented()

    def send(self, data: bytes) -> None:
        self._last_activity = time()
        self._transport.write(data)  # type: ignore

    def close(self) -> None:
        for stream in self.streams.values():
            stream.task.cancel()
        self._transport.close()
        self._timeout_handle.cancel()

    def _after_request(self, stream_id: int, future: asyncio.Future) -> None:
        del self.streams[stream_id]
        if not self.streams:
            self._timeout_handle = self.loop.call_later(self._timeout, self._handle_timeout)
        try:
            exception = future.exception()
        except Exception as error:
            exception = error
        if (
                exception is not None and not isinstance(exception, asyncio.CancelledError) and
                self.logger is not None
        ):
            self.logger.error('Request handling exception', exc_info=exception)

    def response_headers(self) -> List[Tuple[str, str]]:
        return [
            ('date', formatdate(time(), usegmt=True)), ('server', f"quart-{self.protocol}"),
        ]

    def _handle_timeout(self) -> None:
        if time() - self._last_activity > self._timeout:
            self.close()
