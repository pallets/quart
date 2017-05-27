import os

from quart.config import Config, ConfigAttribute

TEST_KEY = 'test_value'


class ConfigInstance:
    value = ConfigAttribute('VALUE')
    config: dict = {}


def test_config_attribute() -> None:
    instance = ConfigInstance()
    instance.value = 'test'
    assert instance.config['VALUE'] == 'test'


def test_config_from_object() -> None:
    config = Config(os.path.dirname(__file__))
    config.from_object(__name__)
    assert config['TEST_KEY'] == 'test_value'


def _check_standard_config(config: Config) -> None:
    assert config['FOO'] == 'bar'
    assert config['BOB'] == 'jeff'


def test_config_from_pyfile() -> None:
    config = Config(os.path.dirname(__file__))
    config.from_pyfile('assets/config.cfg')
    _check_standard_config(config)


def test_config_from_envvar() -> None:
    config = Config(os.path.dirname(__file__))
    os.environ['CONFIG'] = 'assets/config.cfg'
    config.from_envvar('CONFIG')
    _check_standard_config(config)


def test_config_from_json() -> None:
    config = Config(os.path.dirname(__file__))
    config.from_json('assets/config.json')
    _check_standard_config(config)


def test_config_get_namespace() -> None:
    config = Config(os.path.dirname(__file__))
    config['FOO_A'] = 'a'
    config['FOO_BAR'] = 'bar'
    config['BAR'] = 'bar'
    assert config.get_namespace('FOO_') == {'a': 'a', 'bar': 'bar'}
