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
