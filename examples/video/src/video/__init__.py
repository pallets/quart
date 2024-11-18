from quart import Quart
from quart import render_template
from quart import send_file

app = Quart(__name__)


@app.get("/")
async def index():
    return await render_template("index.html")


@app.route("/video.mp4")
async def auto_video():
    return await send_file(app.static_folder / "video.mp4", conditional=True)


def run() -> None:
    app.run()
