from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner

import quart.cli
from quart.app import Quart
from quart.cli import AppGroup, cli, load_dotenv, ScriptInfo


@pytest.fixture(scope="module")
def reset_env() -> None:
    os.environ.pop("QUART_ENV", None)
    os.environ.pop("QUART_DEBUG", None)


@pytest.fixture(name="app")
def loadable_app(monkeypatch: MonkeyPatch) -> Mock:
    app = Mock(spec=Quart)
    app.cli = AppGroup()
    module = Mock()
    module.app = app
    monkeypatch.setattr(quart.cli, "import_module", lambda _: module)
    return app


@pytest.fixture(name="dev_app")
def loadable_dev_app(app: Mock) -> Mock:
    app.debug = True
    return app


@pytest.fixture(name="dev_env")
def dev_env_patch(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("QUART_ENV", "development")


@pytest.fixture(name="debug_env")
def debug_env_patch(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("QUART_DEBUG", "true")


@pytest.fixture(name="no_debug_env")
def no_debug_env_patch(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("QUART_DEBUG", "false")


@pytest.fixture(name="empty_cwd")
def empty_cwd() -> Generator[Path, None, None]:
    directory = tempfile.TemporaryDirectory()
    cwd = os.getcwd()
    os.chdir(directory.name)

    yield Path(directory.name)

    os.chdir(cwd)
    directory.cleanup()


def test_script_info_load_app(app: Mock) -> None:
    info = ScriptInfo("module:app")
    assert info.load_app() == app


def test_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert "Quart" in result.output


def test_run_command(app: Mock) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--app", "module:app", "run"])
    app.run.assert_called_once_with(
        debug=False, host="127.0.0.1", port=5000, certfile=None, keyfile=None, use_reloader=False
    )


def test_run_command_development(dev_app: Mock, dev_env: None) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--app", "module:app", "run"])
    dev_app.run.assert_called_once_with(
        debug=True, host="127.0.0.1", port=5000, certfile=None, keyfile=None, use_reloader=True
    )


def test_run_command_development_debug_disabled(
    dev_app: Mock, dev_env: None, no_debug_env: None
) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--app", "module:app", "run"])
    dev_app.run.assert_called_once_with(
        debug=False, host="127.0.0.1", port=5000, certfile=None, keyfile=None, use_reloader=False
    )


def test_load_dotenv(empty_cwd: Path) -> None:
    value = "dotenv"
    with open(empty_cwd / ".env", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={value}\n")

    load_dotenv()

    assert os.environ.pop("TEST_ENV_VAR", None) == value


def test_load_dotquartenv(empty_cwd: Path) -> None:
    value = "dotquartenv"
    with open(empty_cwd / ".quartenv", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={value}\n")

    load_dotenv()

    assert os.environ.pop("TEST_ENV_VAR", None) == value


def test_load_dotenv_beats_dotquartenv(empty_cwd: Path) -> None:
    env_value = "dotenv"
    quartenv_value = "dotquartenv"

    with open(empty_cwd / ".env", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={env_value}\n")
    with open(empty_cwd / ".quartenv", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={quartenv_value}\n")

    load_dotenv()

    assert os.environ.pop("TEST_ENV_VAR", None) == env_value
