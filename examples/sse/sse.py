import asyncio
from typing import Optional

from quart import Quart, render_template, websocket


app = Quart(__name__)


class ServerSentEvent:

    def __init__(
            self,
            data: str,
            *,
            event: Optional[str]=None,
            id: Optional[int]=None,
            retry: Optional[int]=None,
    ) -> None:
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def encode(self) -> bytes:
        message = f"data: {self.data}"
        if self.event is not None:
            message = f"{message}\nevent: {self.event}"
        if self.id is not None:
            message = f"{message}\nid: {self.id}"
        if self.retry is not None:
            message = f"{message}\nretry: {self.retry}"
        message = f"{message}\r\n\r\n"
        return message.encode('utf-8')



@app.route('/')
async def index():
    return await render_template('index.html')


@app.websocket('/sse')
async def ws():
    async def send_events():
        count = 0
        while True:
            await asyncio.sleep(2)
            event = ServerSentEvent('Hello', id=count)
            yield event.encode()
            count += 1
    return send_events(), {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Transfer-Encoding': 'chunked',
    }


if __name__ == '__main__':
    app.run(port=5000)
