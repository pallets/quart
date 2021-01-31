from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, strategies as strategies

from quart.app import Quart
from quart.json import dumps, htmlsafe_dumps
from quart.json.tag import TaggedJSONSerializer


def test_htmlsafe_dumps() -> None:
    script = htmlsafe_dumps("</script>")
    assert script != '"</script>"'
    assert script == '"\\u003c/script\\u003e"'
    escape = htmlsafe_dumps("&'")
    assert escape != '"&\'"'
    assert escape == '"\\u0026\\u0027"'


@pytest.mark.parametrize("as_ascii, expected", [(True, '"\\ud83c\\udf8a"'), (False, '"🎊"')])
@pytest.mark.asyncio
async def test_ascii_dumps(as_ascii: bool, expected: str) -> None:
    app = Quart(__name__)
    async with app.app_context():
        app.config["JSON_AS_ASCII"] = as_ascii
        assert dumps("🎊") == expected


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
