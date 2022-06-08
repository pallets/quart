from quart import Quart, render_template, request, send_file

app = Quart(__name__)

@app.get("/")
async def index():
    return await render_template("index.html")

@app.route("/video.mp4")
async def auto_video():
    return await send_file(app.static_folder / "video.mp4", conditional=True)

@app.route("/chunked_video.mp4")
async def chunked_video():
    response = await send_file(app.static_folder / "video.mp4")
    await response.make_conditional(request.range, max_partial_size=100_000)
    return response

def run() -> None:
    app.run()
