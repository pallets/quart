import pytest

from quart.app import Quart
from quart.json import dumps, htmlsafe_dumps


def test_htmlsafe_dumps() -> None:
    script = htmlsafe_dumps('</script>')
    assert script != '</script>'
    assert script == '"</script>"'  # Has unicode characters
    escape = htmlsafe_dumps("&'")
    assert escape != "&'"
    assert escape == "\"&'\""  # Has unicode characters


@pytest.mark.parametrize('as_ascii, expected', [(True, '"\\ud83c\\udf8a"'), (False, '"🎊"')])
@pytest.mark.asyncio
async def test_ascii_dumps(as_ascii: bool, expected: str) -> None:
    app = Quart(__name__)
    async with app.app_context():
        app.config['JSON_AS_ASCII'] = as_ascii
        assert dumps('🎊') == expected
