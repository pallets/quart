from __future__ import annotations

import code
import os
import random
import string
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner

import quart.cli
from quart.app import Quart
from quart.cli import __version__, AppGroup, cli, NoAppException, ScriptInfo


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
    app.env == "development"
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
def empty_cwd():
    directory = tempfile.TemporaryDirectory()
    cwd = os.getcwd()
    os.chdir(directory.name)

    yield Path(directory.name)

    os.chdir(cwd)
    directory.cleanup()


def test_script_info_load_app(app: Mock) -> None:
    info = ScriptInfo("module:app")
    assert info.load_app() == app


def test_script_info_load_app_no_app(app: Mock) -> None:
    info = ScriptInfo(None)
    os.environ.pop("QUART_APP", None)
    with pytest.raises(NoAppException):
        info.load_app()


def test_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert str(__version__) in result.output


def test_shell_command(app: Mock, monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    interact = Mock()
    monkeypatch.setattr(code, "interact", interact)
    app.make_shell_context.return_value = {}
    app.import_name = "test"
    os.environ["QUART_APP"] = "module:app"
    runner.invoke(cli, ["shell"])
    app.make_shell_context.assert_called_once()
    interact.assert_called_once()


def test_run_command(app: Mock) -> None:
    runner = CliRunner()
    os.environ["QUART_APP"] = "module:app"
    runner.invoke(cli, ["run"])
    app.run.assert_called_once_with(
        debug=False, host="127.0.0.1", port=5000, certfile=None, keyfile=None, use_reloader=True
    )


def test_run_command_development(dev_app: Mock, dev_env: None) -> None:
    runner = CliRunner()
    os.environ["QUART_APP"] = "module:app"
    runner.invoke(cli, ["run"])
    dev_app.run.assert_called_once_with(
        debug=True, host="127.0.0.1", port=5000, certfile=None, keyfile=None, use_reloader=True
    )


def test_run_command_development_debug_disabled(
    dev_app: Mock, dev_env: None, no_debug_env: None
) -> None:
    runner = CliRunner()
    os.environ["QUART_APP"] = "module:app"
    runner.invoke(cli, ["run"])
    dev_app.run.assert_called_once_with(
        debug=False, host="127.0.0.1", port=5000, certfile=None, keyfile=None, use_reloader=True
    )


def test_load_dotenv(empty_cwd: Path) -> None:
    value = "dotenv"
    with open(empty_cwd / ".env", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={value}\n")

    info = ScriptInfo(None)
    info.load_dotenv_if_exists()

    assert os.environ.pop("TEST_ENV_VAR", None) == value


def test_load_dotquartenv(empty_cwd: Path) -> None:
    value = "dotquartenv"
    with open(empty_cwd / ".quartenv", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={value}\n")

    info = ScriptInfo(None)
    info.load_dotenv_if_exists()

    assert os.environ.pop("TEST_ENV_VAR", None) == value


def test_load_dotenv_beats_dotquartenv(empty_cwd: Path) -> None:
    env_value = "dotenv"
    quartenv_value = "dotquartenv"

    with open(empty_cwd / ".env", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={env_value}\n")
    with open(empty_cwd / ".quartenv", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={quartenv_value}\n")

    info = ScriptInfo(None)
    info.load_dotenv_if_exists()

    assert os.environ.pop("TEST_ENV_VAR", None) == env_value


def test_load_dotenv_inhibited_by_env_var(empty_cwd: Path) -> None:
    env_value = "dotenv"
    quartenv_value = "dotquartenv"

    with open(empty_cwd / ".env", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={env_value}\n")
    with open(empty_cwd / ".quartenv", "w", encoding="utf8") as env:
        env.write(f"TEST_ENV_VAR={quartenv_value}\n")

    os.environ["QUART_SKIP_DOTENV"] = "1"

    info = ScriptInfo(None)
    info.load_dotenv_if_exists()

    assert os.environ.pop("TEST_ENV_VAR", None) is None

    del os.environ["QUART_SKIP_DOTENV"]
