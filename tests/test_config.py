import os

import pytest

from quart.config import Config, ConfigAttribute

FOO = 'bar'
BOB = 'jeff'


class ConfigInstance:
    value = ConfigAttribute('VALUE')
    config: dict = {}


def test_config_attribute() -> None:
    instance = ConfigInstance()
    instance.value = 'test'
    assert instance.config['VALUE'] == 'test'


def _check_standard_config(config: Config) -> None:
    assert config.pop('FOO') == 'bar'
    assert config.pop('BOB') == 'jeff'
    assert len(config) == 0


def test_config_from_object() -> None:
    config = Config(os.path.dirname(__file__))
    config.from_object(__name__)
    _check_standard_config(config)


def test_config_from_pyfile_this() -> None:
    config = Config(os.path.dirname(__file__))
    config.from_pyfile(__file__)
    _check_standard_config(config)


def test_config_from_pyfile_py() -> None:
    config = Config(os.path.dirname(__file__))
    config.from_pyfile('assets/config.py')
    _check_standard_config(config)


def test_config_from_pyfile_cfg() -> None:
    config = Config(os.path.dirname(__file__))
    config.from_pyfile('assets/config.cfg')
    _check_standard_config(config)


def test_config_from_pyfile_no_file() -> None:
    config = Config(os.path.dirname(__file__))
    with pytest.raises(FileNotFoundError):
        config.from_pyfile('assets/no_file.cfg')


def test_config_from_pyfile_directory() -> None:
    config = Config(os.path.dirname(__file__))
    with pytest.raises(IsADirectoryError):
        config.from_pyfile('assets')


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
