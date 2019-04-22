import os
from pathlib import Path

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
    config = Config(Path(__file__).parent)
    config.from_object(__name__)
    _check_standard_config(config)


def test_config_from_pyfile_this() -> None:
    config = Config(Path(__file__).parent)
    config.from_pyfile(__file__)
    _check_standard_config(config)


def test_config_from_pyfile_py() -> None:
    config = Config(Path(__file__).parent)
    config.from_pyfile('assets/config.py')
    _check_standard_config(config)


def test_config_from_pyfile_cfg() -> None:
    config = Config(Path(__file__).parent)
    config.from_pyfile('assets/config.cfg')
    _check_standard_config(config)


def test_config_from_pyfile_no_file() -> None:
    config = Config(Path(__file__).parent)
    with pytest.raises(FileNotFoundError):
        config.from_pyfile('assets/no_file.cfg')


def test_config_from_pyfile_directory() -> None:
    config = Config(Path(__file__).parent)
    with pytest.raises(PermissionError if os.name == 'nt' else IsADirectoryError):
        config.from_pyfile('assets')


def test_config_from_envvar() -> None:
    config = Config(Path(__file__).parent)
    os.environ['CONFIG'] = 'assets/config.cfg'
    config.from_envvar('CONFIG')
    _check_standard_config(config)


def test_config_from_json() -> None:
    config = Config(Path(__file__).parent)
    config.from_json('assets/config.json')
    _check_standard_config(config)


def test_config_get_namespace() -> None:
    config = Config(Path(__file__).parent)
    config['FOO_A'] = 'a'
    config['FOO_BAR'] = 'bar'
    config['BAR'] = 'bar'
    assert config.get_namespace('FOO_') == {'a': 'a', 'bar': 'bar'}
