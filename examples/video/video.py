from quart import Quart, render_template, request, send_file


app = Quart(__name__)


@app.route("/")
async def index():
    return await render_template("index.html")


@app.route("/video.mp4")
async def auto_video():
    # Automatically respond to the request
    return await send_file("video.mp4", conditional=True)


@app.route("/chunked_video.mp4")
async def chunked_video():
    # Force the response to be chunked in a 100_000 bytes max size.
    response = await send_file("video.mp4")
    await response.make_conditional(request.range, max_partial_size=100_000)
    return response
