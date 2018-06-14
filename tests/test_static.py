from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest
from py._path.local import LocalPath

from quart import Quart
from quart.exceptions import NotFound
from quart.static import safe_join, send_file, send_from_directory

ROOT_PATH = Path(__file__).parents[0]


@pytest.mark.parametrize(
    'directory, paths, expected',
    [
        (ROOT_PATH, ['../tests/'], ROOT_PATH),
    ],
)
def test_safe_join(directory: str, paths: List[str], expected: Path) -> None:
    assert safe_join(directory, *paths) == expected


@pytest.mark.parametrize(
    'directory, paths',
    [
        (ROOT_PATH, ['..']),
    ],
)
def test_safe_join_raises(directory: str, paths: List[str]) -> None:
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
