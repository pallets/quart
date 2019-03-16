from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest
from py._path.local import LocalPath

from quart import Quart
from quart.exceptions import NotFound
from quart.static import safe_join, send_file, send_from_directory

ROOT_PATH = Path(__file__).parents[0]


def test_safe_join(tmpdir: LocalPath) -> None:
    directory = tmpdir.realpath()
    tmpdir.join("file.txt").write("something")
    assert safe_join(directory, "file.txt") == Path(directory, "file.txt")


@pytest.mark.parametrize(
    "paths", [[".."], ["..", "other"], ["..", "safes", "file"]],
)
def test_safe_join_raises(paths: List[str], tmpdir: LocalPath) -> None:
    directory = tmpdir.mkdir("safe").realpath()
    tmpdir.mkdir("other")
    tmpdir.mkdir("safes").join("file").write("something")
    with pytest.raises(NotFound):
        safe_join(directory, *paths)


@pytest.mark.asyncio
async def test_send_from_directory_raises() -> None:
    with pytest.raises(NotFound):
        await send_from_directory(str(ROOT_PATH), 'no_file.no')


@pytest.mark.asyncio
async def test_send_file_path(tmpdir: LocalPath) -> None:
    app = Quart(__name__)
    file_ = tmpdir.join('send.img')
    file_.write('something')
    async with app.app_context():
        response = await send_file(Path(file_.realpath()))
    assert (await response.get_data(raw=True)) == file_.read_binary()


@pytest.mark.asyncio
async def test_send_file_as_attachment(tmpdir: LocalPath) -> None:
    app = Quart(__name__)
    file_ = tmpdir.join('send.img')
    file_.write('something')
    async with app.app_context():
        response = await send_file(Path(file_.realpath()), as_attachment=True)
    assert response.headers["content-disposition"] == "attachment; filename=send.img"


@pytest.mark.asyncio
async def test_send_file_as_attachment_name(tmpdir: LocalPath) -> None:
    app = Quart(__name__)
    file_ = tmpdir.join('send.img')
    file_.write('something')
    async with app.app_context():
        response = await send_file(
            Path(file_.realpath()), as_attachment=True, attachment_filename="send.html",
        )
    assert response.headers["content-disposition"] == "attachment; filename=send.html"


@pytest.mark.asyncio
async def test_send_file_mimetype(tmpdir: LocalPath) -> None:
    app = Quart(__name__)
    file_ = tmpdir.join('send.bob')
    file_.write('something')
    async with app.app_context():
        response = await send_file(Path(file_.realpath()), mimetype="application/bob")
    assert (await response.get_data(raw=True)) == file_.read_binary()
    assert response.headers["Content-Type"] == "application/bob"


@pytest.mark.asyncio
async def test_send_file_last_modified(tmpdir: LocalPath) -> None:
    app = Quart(__name__)
    file_ = tmpdir.join('send.img')
    file_.write('something')
    async with app.app_context():
        response = await send_file(str(file_.realpath()))
    mtime = datetime.fromtimestamp(file_.mtime(), tz=timezone.utc)
    mtime = mtime.replace(microsecond=0)
    assert response.last_modified == mtime


@pytest.mark.asyncio
async def test_send_file_last_modified_override(tmpdir: LocalPath) -> None:
    app = Quart(__name__)
    file_ = tmpdir.join('send.img')
    file_.write('something')
    last_modified = datetime(2015, 10, 10, tzinfo=timezone.utc)
    async with app.app_context():
        response = await send_file(str(file_.realpath()), last_modified=last_modified)
    assert response.last_modified == last_modified


@pytest.mark.asyncio
async def test_send_file_max_age(tmpdir: LocalPath) -> None:
    app = Quart(__name__)
    file_ = tmpdir.join('send.img')
    file_.write('something')
    async with app.app_context():
        response = await send_file(str(file_.realpath()))
    assert response.cache_control.max_age == app.send_file_max_age_default.total_seconds()
