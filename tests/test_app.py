import pytest

from quart.app import Quart


def test_endpoint_overwrite() -> None:
    app = Quart(__name__)

    def route() -> str:
        return ''

    app.add_url_rule('/', route, ['GET'], 'index')
    with pytest.raises(AssertionError):
        app.add_url_rule('/a', route, ['GET'], 'index')
