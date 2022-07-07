from __future__ import annotations

import os
from pathlib import Path

import pytest
import toml
from _pytest.monkeypatch import MonkeyPatch

from quart.config import Config, ConfigAttribute

FOO = "bar"
BOB = "jeff"


class ConfigInstance:
    value = ConfigAttribute("VALUE")
    config: dict = {}


def test_config_attribute() -> None:
    instance = ConfigInstance()
    instance.value = "test"
    assert instance.config["VALUE"] == "test"


def _check_standard_config(config: Config) -> None:
    assert config.pop("FOO") == "bar"
    assert config.pop("BOB") == "jeff"
    assert len(config) == 0


def test_config_from_object() -> None:
    config = Config(Path(__file__).parent)
    config.from_object(__name__)
    _check_standard_config(config)


def test_from_prefixed_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("QUART_STRING", "value")
    monkeypatch.setenv("QUART_BOOL", "true")
    monkeypatch.setenv("QUART_INT", "1")
    monkeypatch.setenv("QUART_FLOAT", "1.2")
    monkeypatch.setenv("QUART_LIST", "[1, 2]")
    monkeypatch.setenv("QUART_DICT", '{"k": "v"}')
    monkeypatch.setenv("NOT_QUART_OTHER", "other")

    config = Config(Path(__file__).parent)
    config.from_prefixed_env()

    assert config["STRING"] == "value"
    assert config["BOOL"] is True
    assert config["INT"] == 1
    assert config["FLOAT"] == 1.2
    assert config["LIST"] == [1, 2]
    assert config["DICT"] == {"k": "v"}
    assert "OTHER" not in config


def test_from_prefixed_env_custom_prefix(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("QUART_A", "a")
    monkeypatch.setenv("NOT_QUART_A", "b")

    config = Config(Path(__file__).parent)
    config.from_prefixed_env("NOT_QUART")

    assert config["A"] == "b"


def test_from_prefixed_env_nested(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("QUART_EXIST__ok", "other")
    monkeypatch.setenv("QUART_EXIST__inner__ik", "2")
    monkeypatch.setenv("QUART_EXIST__new__more", '{"k": false}')
    monkeypatch.setenv("QUART_NEW__K", "v")

    config = Config(Path(__file__).parent)
    config["EXIST"] = {"ok": "value", "flag": True, "inner": {"ik": 1}}
    config.from_prefixed_env()

    if os.name != "nt":
        assert config["EXIST"] == {
            "ok": "other",
            "flag": True,
            "inner": {"ik": 2},
            "new": {"more": {"k": False}},
        }
    else:
        # Windows env var keys are always uppercase.
        assert config["EXIST"] == {
            "ok": "value",
            "OK": "other",
            "flag": True,
            "inner": {"ik": 1},
            "INNER": {"IK": 2},
            "NEW": {"MORE": {"k": False}},
        }

    assert config["NEW"] == {"K": "v"}


def test_config_from_pyfile_this() -> None:
    config = Config(Path(__file__).parent)
    config.from_pyfile(__file__)
    _check_standard_config(config)


def test_config_from_pyfile_py() -> None:
    config = Config(Path(__file__).parent)
    config.from_pyfile("assets/config.py")
    _check_standard_config(config)


def test_config_from_pyfile_cfg() -> None:
    config = Config(Path(__file__).parent)
    config.from_pyfile("assets/config.cfg")
    _check_standard_config(config)


def test_config_from_pyfile_no_file() -> None:
    config = Config(Path(__file__).parent)
    with pytest.raises(FileNotFoundError):
        config.from_pyfile("assets/no_file.cfg")


def test_config_from_pyfile_directory() -> None:
    config = Config(Path(__file__).parent)
    with pytest.raises(PermissionError if os.name == "nt" else IsADirectoryError):
        config.from_pyfile("assets")


def test_config_from_envvar() -> None:
    config = Config(Path(__file__).parent)
    os.environ["CONFIG"] = "assets/config.cfg"
    config.from_envvar("CONFIG")
    _check_standard_config(config)


def test_config_from_envvar_not_set_with_silent() -> None:
    config = Config(Path(__file__).parent)
    config.from_envvar("UNKNOWN_CONFIG", silent=True)


def test_config_from_envvar_not_set_without_silent() -> None:
    config = Config(Path(__file__).parent)
    with pytest.raises(RuntimeError):
        config.from_envvar("UNKNOWN_CONFIG")


def test_config_from_json() -> None:
    config = Config(Path(__file__).parent)
    config.from_json("assets/config.json")
    _check_standard_config(config)


def test_config_from_toml() -> None:
    config = Config(Path(__file__).parent)
    config.from_file("assets/config.toml", toml.load)
    _check_standard_config(config)


def test_config_get_namespace() -> None:
    config = Config(Path(__file__).parent)
    config["FOO_A"] = "a"
    config["FOO_BAR"] = "bar"
    config["BAR"] = "bar"
    assert config.get_namespace("FOO_") == {"a": "a", "bar": "bar"}
