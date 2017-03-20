import asyncio
from json import dumps
from typing import Any, Optional

from typing import TYPE_CHECKING

from .wrappers import Request, Response

if TYPE_CHECKING:
    from .app import Quart  # noqa

sentinel = object()


class TestClient:

    def __init__(self, app: 'Quart', use_cookies: bool=True) -> None:
        self.use_cookies = use_cookies
        self.app = app

    async def open(
        self, path: str, *, method: str='GET', headers: Optional[dict]=None, json: Any=sentinel
    ) -> Response:
        headers = headers or {}
        body: asyncio.Future = asyncio.Future()
        if json is not sentinel:
            data = dumps(json).encode('utf-8')
            headers['Content-Type'] = 'application/json'
            body.set_result(data)
        else:
            body.set_result(b'')
        request = Request(method, path, headers, body)
        return await asyncio.ensure_future(self.app.handle_request(request))

    async def delete(self, *args: Any, **kwargs: Any) -> Response:
        return await self.open(*args, method='DELETE', **kwargs)

    async def get(self, *args: Any, **kwargs: Any) -> Response:
        return await self.open(*args, method='GET', **kwargs)

    async def head(self, *args: Any, **kwargs: Any) -> Response:
        return await self.open(*args, method='HEAD', **kwargs)

    async def options(self, *args: Any, **kwargs: Any) -> Response:
        return await self.open(*args, method='OPTIONS', **kwargs)

    async def patch(self, *args: Any, **kwargs: Any) -> Response:
        return await self.open(*args, method='PATCH', **kwargs)

    async def post(self, *args: Any, **kwargs: Any) -> Response:
        return await self.open(*args, method='POST', **kwargs)

    async def put(self, *args: Any, **kwargs: Any) -> Response:
        return await self.open(*args, method='PUT', **kwargs)

    async def trace(self, *args: Any, **kwargs: Any) -> Response:
        return await self.open(*args, method='TRACE', **kwargs)
