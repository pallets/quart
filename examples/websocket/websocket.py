from quart import Quart, render_template, websocket


app = Quart(__name__)


@app.route('/')
async def index():
    return await render_template('index.html')


@app.websocket('/ws')
async def ws():
    while True:
        data = await websocket.receive()
        await websocket.send(f"echo {data}")


if __name__ == '__main__':
    app.run(port=5000)
