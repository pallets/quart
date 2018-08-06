import os

from quart.app import Quart


def test_env_defaults() -> None:
    if 'QUART_ENV' in os.environ:
        del os.environ['QUART_ENV']
    if 'QUART_DEBUG' in os.environ:
        del os.environ['QUART_DEBUG']

    app = Quart(__name__)

    assert app.env == app.config['ENV']
    assert app.env == 'production'
    assert app.debug is False


def test_development_environ_set_debug_true_if_debug_unset() -> None:
    os.environ['QUART_ENV'] = 'development'
    app = Quart(__name__)

    assert app.env == app.config['ENV']
    assert app.env == 'development'
    assert app.debug is True


def test_setting_debug_env_overrides_development_env_behaviour() -> None:
    os.environ['QUART_ENV'] = 'development'
    os.environ['QUART_DEBUG'] = 'false'

    app = Quart(__name__)

    assert app.env == app.config['ENV']
    assert app.env == 'development'
    assert app.debug is False
