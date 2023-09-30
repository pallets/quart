from __future__ import annotations

import ast
import asyncio
import code
import functools
import inspect
import os
import platform
import re
import sys
import traceback
from importlib import import_module
from operator import attrgetter
from types import ModuleType
from typing import Any, Callable, TYPE_CHECKING

import click
from click.core import ParameterSource

from .globals import current_app
from .helpers import get_debug_flag, get_load_dotenv

try:
    from importlib.metadata import version
except ModuleNotFoundError:
    from importlib_metadata import version  # type: ignore

if TYPE_CHECKING:
    from .app import Quart  # noqa: F401


class NoAppException(click.UsageError):
    pass


def _called_with_wrong_args(f: Callable) -> bool:
    """Check whether calling a function raised a ``TypeError`` because
    the call failed or because something in the factory raised the
    error.
    :param f: The function that was called.
    :return: ``True`` if the call failed.
    """
    tb = sys.exc_info()[2]

    try:
        while tb is not None:
            if tb.tb_frame.f_code is f.__code__:
                # In the function, it was called successfully.
                return False

            tb = tb.tb_next

        # Didn't reach the function.
        return True
    finally:
        # Delete tb to break a circular reference.
        # https://docs.python.org/2/library/sys.html#sys.exc_info
        del tb


def find_best_app(module: ModuleType) -> Quart:
    from .app import Quart

    for attr_name in ("app", "application"):
        app = getattr(module, attr_name, None)

        if isinstance(app, Quart):
            return app

    matches = [value for value in module.__dict__.values() if isinstance(value, Quart)]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        raise NoAppException(
            "Detected multiple Quart applications in module"
            f" '{module.__name__}'. Use '{module.__name__}:name'"
            " to specify the correct one."
        )

    for attr_name in ("create_app", "make_app"):
        app_factory = getattr(module, attr_name, None)

        if inspect.isfunction(app_factory):
            try:
                app = app_factory()

                if isinstance(app, Quart):
                    return app
            except TypeError as error:
                if not _called_with_wrong_args(app_factory):
                    raise

                raise NoAppException(
                    f"Detected factory '{attr_name}' in module '{module.__name__}',"
                    " but could not call it without arguments. Use"
                    f" '{module.__name__}:{attr_name}(args)'"
                    " to specify arguments."
                ) from error

    raise NoAppException(
        "Failed to find Quart application or factory in module"
        f" '{module.__name__}'. Use '{module.__name__}:name'"
        " to specify one."
    )


def find_app_by_string(module: ModuleType, app_name: str) -> Quart:
    from .app import Quart

    try:
        expr = ast.parse(app_name.strip(), mode="eval").body
    except SyntaxError:
        raise NoAppException(
            f"Failed to parse {app_name!r} as an attribute name or function call."
        ) from None

    if isinstance(expr, ast.Name):
        name = expr.id
        args = []
        kwargs = {}
    elif isinstance(expr, ast.Call):
        # Ensure the function name is an attribute name only.
        if not isinstance(expr.func, ast.Name):
            raise NoAppException(f"Function reference must be a simple name: {app_name!r}.")

        name = expr.func.id

        # Parse the positional and keyword arguments as literals.
        try:
            args = [ast.literal_eval(arg) for arg in expr.args]
            kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in expr.keywords}
        except ValueError:
            # literal_eval gives cryptic error messages, show a generic
            # message with the full expression instead.
            raise NoAppException(
                f"Failed to parse arguments as literal values: {app_name!r}."
            ) from None
    else:
        raise NoAppException(f"Failed to parse {app_name!r} as an attribute name or function call.")

    try:
        attr = getattr(module, name)
    except AttributeError as e:
        raise NoAppException(f"Failed to find attribute {name!r} in {module.__name__!r}.") from e

    # If the attribute is a function, call it with any args and kwargs
    # to get the real application.
    if inspect.isfunction(attr):
        try:
            app = attr(*args, **kwargs)
        except TypeError as e:
            if not _called_with_wrong_args(attr):
                raise

            raise NoAppException(
                f"The factory {app_name!r} in module"
                f" {module.__name__!r} could not be called with the"
                " specified arguments."
            ) from e
    else:
        app = attr

    if isinstance(app, Quart):
        return app

    raise NoAppException(
        f"A valid Quart application was not obtained from '{module.__name__}:{app_name}'."
    )


def locate_app(module_name: str, app_name: str) -> Quart | None:
    try:
        module = import_module(module_name)
    except ImportError:
        # Reraise the ImportError if it occurred within the imported module.
        # Determine this by checking whether the trace has a depth > 1.
        if sys.exc_info()[2].tb_next:
            raise NoAppException(
                f"While importing {module_name!r}, an ImportError was"
                f" raised:\n\n{traceback.format_exc()}"
            ) from None
        else:
            raise NoAppException(f"Could not import {module_name!r}.") from None
    else:
        if app_name is None:
            return find_best_app(module)
        else:
            return find_app_by_string(module, app_name)


def prepare_import(path: str) -> str:
    """Given a filename this will try to calculate the python path, add it
    to the search path and return the actual module name that is expected.
    """
    path = os.path.realpath(path)

    fname, ext = os.path.splitext(path)
    if ext == ".py":
        path = fname

    if os.path.basename(path) == "__init__":
        path = os.path.dirname(path)

    module_name = []

    # move up until outside package structure (no __init__.py)
    while True:
        path, name = os.path.split(path)
        module_name.append(name)

        if not os.path.exists(os.path.join(path, "__init__.py")):
            break

    if sys.path[0] != path:
        sys.path.insert(0, path)

    return ".".join(module_name[::-1])


class ScriptInfo:
    def __init__(
        self,
        app_import_path: str | None = None,
        create_app: Callable[..., Quart] | None = None,
        set_debug_flag: bool = True,
    ) -> None:
        self.app_import_path = app_import_path
        self.create_app = create_app
        self.data: dict[Any, Any] = {}
        self.set_debug_flag = set_debug_flag
        self._loaded_app: Quart | None = None

    def load_app(self) -> Quart:
        if self._loaded_app is not None:
            return self._loaded_app

        if self.create_app is not None:
            app = self.create_app()
        else:
            if self.app_import_path:
                path, name = (re.split(r":(?![\\/])", self.app_import_path, 1) + [None])[:2]
                import_name = prepare_import(path)
                app = locate_app(import_name, name)
            else:
                import_name = prepare_import("app.py")
                app = locate_app(import_name, None)

        if not app:
            raise NoAppException(
                "Could not locate a Quart application. Use the"
                " 'quart --app' option, 'QUART_APP' environment"
                " variable, or an 'app.py' file in the"
                " current directory."
            )

        if self.set_debug_flag:
            # Update the app's debug flag through the descriptor so that
            # other values repopulate as well.
            app.debug = get_debug_flag()

        self._loaded_app = app
        return app


pass_script_info = click.make_pass_decorator(ScriptInfo, ensure=True)


def with_appcontext(fn: Callable | None = None) -> Callable:
    # decorator was used with parenthesis
    if fn is None:
        return with_appcontext

    @click.pass_context
    def decorator(__ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        async def _inner() -> Any:
            async with __ctx.ensure_object(ScriptInfo).load_app().app_context():
                try:
                    return __ctx.invoke(fn, *args, **kwargs)
                except RuntimeError as error:
                    if error.args[0] == "Cannot run the event loop while another loop is running":
                        click.echo(
                            "The appcontext cannot be used with a command that runs an event loop. "
                            "See quart#361 for more details"
                        )
                    raise

        return asyncio.run(_inner())

    return functools.update_wrapper(decorator, fn)


class AppGroup(click.Group):
    """This works similar to a regular click :class:`~click.Group` but it
    changes the behavior of the :meth:`command` decorator so that it
    automatically wraps the functions in :func:`with_appcontext`.

    Not to be confused with :class:`QuartGroup`.
    """

    def command(self, *args: Any, **kwargs: Any) -> Callable:  # type: ignore
        """This works exactly like the method of the same name on a regular
        :class:`click.Group` but it wraps callbacks in :func:`with_appcontext`
        if it's enabled by passing ``with_appcontext=True``.
        """
        wrap_for_ctx = kwargs.pop("with_appcontext", False)

        def decorator(f: Callable) -> Callable:
            if wrap_for_ctx:
                f = with_appcontext(f)
            return click.Group.command(self, *args, **kwargs)(f)

        return decorator

    def group(self, *args: Any, **kwargs: Any) -> Callable:  # type: ignore
        kwargs.setdefault("cls", AppGroup)
        return super().group(*args, **kwargs)


def get_version(ctx: Any, param: Any, value: Any) -> None:
    if not value or ctx.resilient_parsing:
        return

    quart_version = version("quart")
    werkzeug_version = version("werkzeug")

    click.echo(
        f"Python {platform.python_version()}\n"
        f"Quart {quart_version}\n"
        f"Werkzeug {werkzeug_version}",
        color=ctx.color,
    )
    ctx.exit()


version_option = click.Option(
    ["--version"],
    help="Show the Quart version",
    expose_value=False,
    callback=get_version,
    is_flag=True,
    is_eager=True,
)


def _set_app(ctx: click.Context, param: click.Option, value: str | None) -> str | None:
    if value is None:
        return None

    info = ctx.ensure_object(ScriptInfo)
    info.app_import_path = value
    return value


# This option is eager so the app will be available if --help is given.
# --help is also eager, so --app must be before it in the param list.
# no_args_is_help bypasses eager processing, so this option must be
# processed manually in that case to ensure QUART_APP gets picked up.
_app_option = click.Option(
    ["-A", "--app"],
    metavar="IMPORT",
    help=(
        "The QUART application or factory function to load, in the form 'module:name'."
        " Module can be a dotted import or file path. Name is not required if it is"
        " 'app', 'application', 'create_app', or 'make_app', and can be 'name(args)' to"
        " pass arguments."
    ),
    is_eager=True,
    expose_value=False,
    callback=_set_app,
)


def _set_debug(ctx: click.Context, param: click.Option, value: bool) -> bool | None:
    # If the flag isn't provided, it will default to False. Don't use
    # that, let debug be set by env in that case.
    source = ctx.get_parameter_source(param.name)

    if source is not None and source in (
        ParameterSource.DEFAULT,
        ParameterSource.DEFAULT_MAP,
    ):
        return None

    # Set with env var instead of ScriptInfo.load so that it can be
    # accessed early during a factory function.
    os.environ["QUART_DEBUG"] = "1" if value else "0"
    return value


_debug_option = click.Option(
    ["--debug/--no-debug"],
    help="Set 'app.debug' separately from '--env'.",
    expose_value=False,
    callback=_set_debug,
)


def _env_file_callback(ctx: click.Context, param: click.Option, value: str | None) -> str | None:
    if value is None:
        return None

    import importlib

    try:
        importlib.import_module("dotenv")
    except ImportError:
        raise click.BadParameter(
            "python-dotenv must be installed to load an env file.",
            ctx=ctx,
            param=param,
        ) from None

    # Don't check QUART_SKIP_DOTENV, that only disables automatically
    # loading .env and .quartenv files.
    load_dotenv(value)
    return value


# This option is eager so env vars are loaded as early as possible to be
# used by other options.
_env_file_option = click.Option(
    ["-e", "--env-file"],
    type=click.Path(exists=True, dir_okay=False),
    help="Load environment variables from this file. python-dotenv must be installed.",
    is_eager=True,
    expose_value=False,
    callback=_env_file_callback,
)


class QuartGroup(AppGroup):
    def __init__(
        self,
        add_default_commands: bool = True,
        create_app: Callable[..., Quart] | None = None,
        add_version_option: bool = True,
        load_dotenv: bool = True,
        set_debug_flag: bool = True,
        **extra: Any,
    ) -> None:
        params = list(extra.pop("params", None) or ())
        # Processing is done with option callbacks instead of a group
        # callback. This allows users to make a custom group callback
        # without losing the behavior. --env-file must come first so
        # that it is eagerly evaluated before --app.
        params.extend((_env_file_option, _app_option, _debug_option))

        if add_version_option:
            params.append(version_option)

        if "context_settings" not in extra:
            extra["context_settings"] = {}

        extra["context_settings"].setdefault("auto_envvar_prefix", "QUART")

        super().__init__(params=params, **extra)

        self.create_app = create_app
        self.load_dotenv = load_dotenv
        self.set_debug_flag = set_debug_flag

        if add_default_commands:
            self.add_command(run_command)
            self.add_command(shell_command)
            self.add_command(routes_command)

        self._loaded_plugin_commands = False

    def _load_plugin_commands(self) -> None:
        if self._loaded_plugin_commands:
            return

        if sys.version_info >= (3, 10):
            from importlib.metadata import entry_points
        else:
            # Use a backport on Python < 3.10. We technically have
            # importlib.metadata on 3.8+, but the API changed in 3.10,
            # so use the backport for consistency.
            from importlib_metadata import entry_points

        for point in entry_points(group="quart.commands"):
            self.add_command(point.load(), point.name)

        self._loaded_plugin_commands = True

    def get_command(self, ctx: click.Context, name: str) -> click.Command:
        self._load_plugin_commands()

        rv = super().get_command(ctx, name)

        if rv is not None:
            return rv

        info = ctx.ensure_object(ScriptInfo)

        # Look up commands provided by the app, showing an error and
        # continuing if the app couldn't be loaded.
        try:
            app = info.load_app()
        except NoAppException as e:
            click.secho(f"Error: {e.format_message()}\n", err=True, fg="red")
            return None

        return app.cli.get_command(ctx, name)

    def list_commands(self, ctx: click.Context) -> list[str]:
        self._load_plugin_commands()

        rv = set(super().list_commands(ctx))
        info = ctx.ensure_object(ScriptInfo)

        # Add commands provided by the app, showing an error and
        # continuing if the app couldn't be loaded.
        try:
            rv.update(info.load_app().cli.list_commands(ctx))
        except NoAppException as e:
            # When an app couldn't be loaded, show the error message
            # without the traceback.
            click.secho(f"Error: {e.format_message()}\n", err=True, fg="red")
        except Exception:
            # When any other errors occurred during loading, show the
            # full traceback.
            click.secho(f"{traceback.format_exc()}\n", err=True, fg="red")

        return sorted(rv)

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: click.Context | None = None,
        **extra: Any,
    ) -> click.Context:
        # Attempt to load .env and .quartenv files. The --env-file
        # option can cause another file to be loaded.
        if get_load_dotenv(self.load_dotenv):
            load_dotenv()

        if "obj" not in extra and "obj" not in self.context_settings:
            extra["obj"] = ScriptInfo(
                create_app=self.create_app, set_debug_flag=self.set_debug_flag
            )

        return super().make_context(info_name, args, parent=parent, **extra)

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if not args and self.no_args_is_help:
            # Attempt to load --env-file and --app early in case they
            # were given as env vars. Otherwise no_args_is_help will not
            # see commands from app.cli.
            _env_file_option.handle_parse_result(ctx, {}, [])
            _app_option.handle_parse_result(ctx, {}, [])

        return super().parse_args(ctx, args)


def load_dotenv(path: str | os.PathLike | None = None) -> bool:
    """Load "dotenv" files in order of precedence to set environment variables.
    If an env var is already set it is not overwritten, so earlier files in the
    list are preferred over later files.
    This is a no-op if `python-dotenv`_ is not installed.
    .. _python-dotenv: https://github.com/theskumar/python-dotenv#readme
    :param path: Load the file at this location instead of searching.
    :return: ``True`` if a file was loaded.
    """
    try:
        import dotenv
    except ImportError:
        if path or os.path.isfile(".env") or os.path.isfile(".quartenv"):
            click.secho(
                " * Tip: There are .env or .quartenv files present."
                ' Do "pip install python-dotenv" to use them.',
                fg="yellow",
                err=True,
            )

        return False

    # Always return after attempting to load a given path, don't load
    # the default files.
    if path is not None:
        if os.path.isfile(path):
            return dotenv.load_dotenv(path, encoding="utf-8")

        return False

    loaded = False

    for name in (".env", ".quartenv"):
        path = dotenv.find_dotenv(name, usecwd=True)

        if not path:
            continue

        dotenv.load_dotenv(path, encoding="utf-8")
        loaded = True

    return loaded  # True if at least one file was located and loaded.


@click.command("run", short_help="Run a development server.")
@click.option("--host", "-h", default="127.0.0.1", help="The interface to bind to.")
@click.option("--port", "-p", default=5000, help="The port to bind to.")
@click.option(
    "--certfile",
    "--cert",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Specify a certificate file to use HTTPS.",
)
@click.option(
    "--keyfile",
    "--key",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="The key file to use when specifying a certificate.",
)
@click.option(
    "--reload/--no-reload",
    default=None,
    help="Enable or disable the reloader",
)
@pass_script_info
def run_command(
    info: ScriptInfo,
    host: str,
    port: int,
    reload: bool,
    keyfile: str,
    certfile: str,
) -> None:
    """Run a local development server."""
    app = info.load_app()
    debug = get_debug_flag()

    if reload is None:
        reload = debug

    app.run(
        debug=debug, host=host, port=port, certfile=certfile, keyfile=keyfile, use_reloader=reload
    )


@click.command("shell", short_help="Run a shell in the app context.")
@with_appcontext
def shell_command() -> None:
    """Run an interactive Python shell in the context of a given
    Quart application.  The application will populate the default
    namespace of this shell according to its configuration.
    This is useful for executing small snippets of management code
    without having to manually configure the application.
    """
    banner = (
        f"Python {sys.version} on {sys.platform}\n"
        f"App: {current_app.import_name}\n"
        f"Instance: {current_app.instance_path}"
    )
    ctx: dict = {}

    # Support the regular Python interpreter startup script if someone
    # is using it.
    startup = os.environ.get("PYTHONSTARTUP")
    if startup and os.path.isfile(startup):
        with open(startup) as f:
            eval(compile(f.read(), startup, "exec"), ctx)

    ctx.update(current_app.make_shell_context())

    # Site, customize, or startup script can set a hook to call when
    # entering interactive mode. The default one sets up readline with
    # tab and history completion.
    interactive_hook = getattr(sys, "__interactivehook__", None)

    if interactive_hook is not None:
        try:
            import readline
            from rlcompleter import Completer
        except ImportError:
            pass
        else:
            # rlcompleter uses __main__.__dict__ by default, which is
            # quart.__main__. Use the shell context instead.
            readline.set_completer(Completer(ctx).complete)

        interactive_hook()

    code.interact(banner=banner, local=ctx)


@click.command("routes", short_help="Show the routes for the app.")
@click.option(
    "--sort",
    "-s",
    type=click.Choice(("endpoint", "methods", "domain", "rule", "match")),
    default="endpoint",
    help=(
        'Method to sort routes by. "match" is the order that Quart will match '
        "routes when dispatching a request."
    ),
)
@click.option("--all-methods", is_flag=True, help="Show HEAD and OPTIONS methods.")
@with_appcontext
def routes_command(sort: str, all_methods: bool) -> None:
    """Show all registered routes with endpoints and methods."""

    rules = list(current_app.url_map.iter_rules())
    if not rules:
        click.echo("No routes were registered.")
        return

    ignored_methods = set() if all_methods else {"HEAD", "OPTIONS"}
    host_matching = current_app.url_map.host_matching
    has_domain = any(rule.host if host_matching else rule.subdomain for rule in rules)

    if sort in ("endpoint", "rule", "domain"):
        rules = sorted(rules, key=attrgetter(sort))
    elif sort == "methods":
        rules = sorted(rules, key=lambda rule: sorted(rule.methods))

    headers = ["Endpoint", "Methods"]
    if has_domain:
        headers.append("Host" if host_matching else "Subdomain")
    headers.append("Rule")

    rows = []
    for rule in rules:
        row = [rule.endpoint, ", ".join(sorted(rule.methods - ignored_methods))]
        if has_domain:
            row.append((rule.host if host_matching else rule.subdomain) or "")
        row.append(rule.rule)
        rows.append(row)

    rows.insert(0, headers)
    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    rows.insert(1, ["-" * w for w in widths])
    template = "  ".join(f"{{{i}:<{w}}}" for i, w in enumerate(widths))

    for row in rows:
        click.echo(template.format(*row))


cli = QuartGroup(
    name="quart",
    help="""\
A general utility script for Quart applications.
An application to load must be given with the '--app' option,
'QUART_APP' environment variable, or with an 'app.py' file
in the current directory.
""",
)


def main() -> None:
    cli.main()


if __name__ == "__main__":
    main()
