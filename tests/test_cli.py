import code
import os
from unittest.mock import Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner

import quart.cli
from quart.__about__ import __version__
from quart.cli import AppGroup, cli, NoAppException, ScriptInfo


@pytest.fixture(name='app')
def loadable_app(monkeypatch: MonkeyPatch) -> Mock:
    app = Mock()
    app.cli = AppGroup()
    module = Mock()
    module.app = app
    monkeypatch.setattr(quart.cli, 'import_module', lambda _: module)
    return app


def test_script_info_load_app(app: Mock) -> None:
    info = ScriptInfo('module:app')
    assert info.load_app() == app


def test_script_info_load_app_no_app(app: Mock) -> None:
    info = ScriptInfo(None)
    os.environ.pop('QUART_APP', None)
    with pytest.raises(NoAppException):
        info.load_app()


def test_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])
    assert str(__version__) in result.output


def test_shell_command(app: Mock, monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    interact = Mock()
    monkeypatch.setattr(code, 'interact', interact)
    app.make_shell_context.return_value = {}
    os.environ['QUART_APP'] = 'module:app'
    runner.invoke(cli, ['shell'])
    app.make_shell_context.assert_called_once()
    interact.assert_called_once()


def test_run_command(app: Mock) -> None:
    runner = CliRunner()
    os.environ['QUART_APP'] = 'module:app'
    runner.invoke(cli, ['run'])
    app.run.assert_called_once()
