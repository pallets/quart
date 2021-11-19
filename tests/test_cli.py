from __future__ import annotations

import code
import os
import sys
from unittest.mock import Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner
import quart.cli
from quart.app import Quart
from quart.cli import AppGroup, NoAppException, ScriptInfo, __version__, cli


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


def test_shell_ipython_command(app: Mock, monkeypatch: MonkeyPatch) -> None:
    import IPython

    runner = CliRunner()
    start = Mock()
    monkeypatch.setattr(IPython, "start_ipython", start)

    app.make_shell_context.return_value = {}
    app.import_name = "test"
    os.environ["QUART_APP"] = "module:app"
    runner.invoke(cli, ["shell", "--ipython"])

    app.make_shell_context.assert_called_once()
    start.assert_called_once()


def test_run_command(app: Mock) -> None:
    runner = CliRunner()
    os.environ["QUART_APP"] = "module:app"
    runner.invoke(cli, ["run"])
    app.run.assert_called_once_with(
        debug=False, host="127.0.0.1", port=5000, certfile=None, keyfile=None,
        use_reloader=True
    )


def test_run_command_development(dev_app: Mock, dev_env: None) -> None:
    runner = CliRunner()
    os.environ["QUART_APP"] = "module:app"
    runner.invoke(cli, ["run"])
    dev_app.run.assert_called_once_with(
        debug=True, host="127.0.0.1", port=5000, certfile=None, keyfile=None,
        use_reloader=True
    )


def test_run_command_development_debug_disabled(
    dev_app: Mock, dev_env: None, no_debug_env: None
) -> None:
    runner = CliRunner()
    os.environ["QUART_APP"] = "module:app"
    runner.invoke(cli, ["run"])
    dev_app.run.assert_called_once_with(
        debug=False, host="127.0.0.1", port=5000, certfile=None, keyfile=None,
        use_reloader=True
    )
