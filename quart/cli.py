import code
import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, TYPE_CHECKING

import click

from .__about__ import __version__
from .helpers import get_debug_flag

if TYPE_CHECKING:
    from .app import Quart  # noqa: F401


class NoAppException(click.UsageError):

    def __init__(self) -> None:
        super().__init__(
            'Could not locate a Quart application as the QUART_APP environment '
            'variable has either not been set or provided or does not point to '
            'a valid application.\n'
            'Please set it to module_name:app_name or module_name:factory_function()'
        )


class ScriptInfo:

    def __init__(
            self,
            app_import_path: Optional[str]=None,
            create_app: Optional[Callable]=None,
    ) -> None:
        self.app_import_path = app_import_path or os.environ.get('QUART_APP')
        self.create_app = create_app
        self.data: dict = {}
        self._app: Optional['Quart'] = None

    def load_app(self) -> 'Quart':
        if self._app is None:
            if self.create_app is not None:
                self._app = self.create_app()
            else:
                try:
                    module_name, app_name = self.app_import_path.split(':', 1)
                except ValueError:
                    module_name, app_name = self.app_import_path, 'app'
                except AttributeError:
                    raise NoAppException()

                module_path = Path(module_name).resolve()
                sys.path.insert(0, str(module_path.parent))
                if module_path.is_file():
                    import_name = module_path.with_suffix('').name
                else:
                    import_name = module_path.name
                try:
                    module = import_module(import_name)
                except ModuleNotFoundError as error:
                    if error.name == import_name:  # type: ignore
                        raise NoAppException()
                    else:
                        raise

                try:
                    self._app = eval(app_name, vars(module))
                except NameError:
                    raise NoAppException()

        if self._app is None:
            raise NoAppException()

        self._app.debug = get_debug_flag()

        return self._app


pass_script_info = click.make_pass_decorator(ScriptInfo, ensure=True)


class AppGroup(click.Group):

    def group(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault('cls', AppGroup)
        return super().group(self, *args, **kwargs)


def get_version(ctx: Any, param: Any, value: Any) -> None:
    if not value or ctx.resilient_parsing:
        return
    message = f"Quart {__version__}"
    click.echo(message, color=ctx.color)
    ctx.exit()


version_option = click.Option(
    ['--version'], help='Show the Quart version', expose_value=False,
    callback=get_version, is_flag=True, is_eager=True,
)


class QuartGroup(AppGroup):

    def __init__(
            self,
            add_default_commands: bool=True,
            create_app: Optional[Callable]=None,
            add_version_option: bool=True,
            *,
            params: Optional[List]=None,
            **kwargs: Any,
    ) -> None:
        params = params or []
        if add_version_option:
            params.append(version_option)
        super().__init__(params=params, **kwargs)
        self.create_app = create_app

        if add_default_commands:
            self.add_command(run_command)
            self.add_command(shell_command)

    def get_command(self, ctx: click.Context, name: str) -> click.Command:
        """Return the relevant command given the context and name.

        .. warning::

            This differs substaintially from Flask in that it allows
            for the inbuilt commands to be overridden.
        """
        info = ctx.ensure_object(ScriptInfo)
        command = None
        try:
            command = info.load_app().cli.get_command(ctx, name)
        except NoAppException:
            pass
        if command is None:
            command = super().get_command(ctx, name)
        return command

    def list_commands(self, ctx: click.Context) -> Iterable[str]:
        commands = set(click.Group.list_commands(self, ctx))
        info = ctx.ensure_object(ScriptInfo)
        commands.update(info.load_app().cli.list_commands(ctx))
        return commands

    def main(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault('obj', ScriptInfo(create_app=self.create_app))
        return super().main(*args, **kwargs)


@click.command('run', short_help='Start and run a development server.')
@click.option('--host', '-h', default='127.0.0.1', help='The interface to serve on.')
@click.option('--port', '-p', default=5000, help='The port to serve on.')
@pass_script_info
def run_command(info: ScriptInfo, host: str, port: int) -> None:
    app = info.load_app()
    app.run(
        debug=True, access_log_format="%(h)s %(r)s %(s)s %(b)s %(D)s", host=host, port=port,
        use_reloader=True,
    )


@click.command('shell', short_help='Open a shell within the app context.')
@pass_script_info
def shell_command(info: ScriptInfo) -> None:
    app = info.load_app()
    context = {}
    context.update(app.make_shell_context())

    banner = f"Python {sys.version} on {sys.platform} running {app.import_name}"
    code.interact(banner=banner, local=context)


cli = QuartGroup(
    help="""\
Utility functions for Quart applications.

This will load the app defined in the QUART_APP environment
variable. The QUART_APP variable follows the Gunicorn standard of
`module_name:application_name` e.g. `hello:app`.

\b
{prefix}{cmd} QUART_APP=hello:app
{prefix}{cmd} QUART_DEBUG=1
{prefix}quart run
    """.format(
        cmd='export' if os.name == 'posix' else 'set',
        prefix='$ ' if os.name == 'posix' else '> ',
    ),
)


def main(as_module: bool=False) -> None:
    args = sys.argv[1:]

    if as_module:
        name = 'python -m quart'
        sys.argv = ['-m', 'quart'] + args
    else:
        name = None

    cli.main(args=args, prog_name=name)


if __name__ == '__main__':
    main(as_module=True)
