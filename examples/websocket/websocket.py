from quart import Quart, render_template, websocket
from functools import partial, wraps


app = Quart(__name__)


connected_websockets = set()

def collect_websocket(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global connected_websockets
        queue = asyncio.Queue()
        connected_websockets.add(queue)
        try:
            return await func(queue, *args, **kwargs)
        finally:
            connected_websockets.remove(queue)
    return wrapper

async def broadcast(message):
    for queue in connected_websockets:
        await queue.put(message)


@app.route('/')
async def index():
    return await render_template('index.html')


@app.websocket('/ws')
async def ws():
    while True:
        data = await websocket.receive()
        await websocket.send(f"echo {data}")


@app.websocket('/api/v2/ws')
@collect_websocket
async def ws_v2(queue):
    while True:
        data = await queue.get()
        await websocket.send(data)



if __name__ == '__main__':
    app.run(port=5000)
