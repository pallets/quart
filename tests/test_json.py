from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, strategies as strategies

from quart.app import Quart
from quart.json.tag import TaggedJSONSerializer


@pytest.mark.parametrize("as_ascii, expected", [(True, '"\\ud83c\\udf8a"'), (False, '"🎊"')])
async def test_ascii_dumps(as_ascii: bool, expected: str) -> None:
    app = Quart(__name__)
    async with app.app_context():
        app.json.ensure_ascii = as_ascii  # type: ignore
        assert app.json.dumps("🎊") == expected


@given(
    value=strategies.one_of(
        strategies.datetimes(),
        strategies.uuids(),
        strategies.binary(),
        strategies.tuples(strategies.integers()),
    )
)
def test_jsonserializer(value: Any) -> None:
    serializer = TaggedJSONSerializer()
    assert serializer.loads(serializer.dumps(value)) == value
