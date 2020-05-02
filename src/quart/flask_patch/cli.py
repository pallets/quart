from types import FunctionType

from quart.cli import AppGroup, QuartGroup, run_command, ScriptInfo, shell_command  # noqa: F401

FlaskGroup = QuartGroup


def with_appcontext(fn: FunctionType) -> FunctionType:
    return fn
