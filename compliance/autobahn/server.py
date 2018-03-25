from quart import Quart, websocket

app = Quart(__name__)


@app.websocket('/')
async def ws():
    while True:
        data = await websocket.receive()
        await websocket.send(data)


if __name__ == '__main__':
    app.run(port=5000)
