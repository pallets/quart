from pathlib import Path
from typing import List

import pytest

from quart.exceptions import NotFound
from quart.static import safe_join, send_from_directory

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
