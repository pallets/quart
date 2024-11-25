from __future__ import annotations

import os
import typing as t
from collections import defaultdict
from datetime import timedelta

from aiofiles import open as async_open
from aiofiles.base import AiofilesContextManager
from flask.sansio.app import App
from flask.sansio.blueprints import Blueprint as SansioBlueprint  # noqa
from flask.sansio.blueprints import BlueprintSetupState as BlueprintSetupState  # noqa
from flask.sansio.scaffold import setupmethod

from .cli import AppGroup
from .globals import current_app
from .helpers import send_from_directory
from .typing import AfterServingCallable
from .typing import AfterWebsocketCallable
from .typing import AppOrBlueprintKey
from .typing import BeforeServingCallable
from .typing import BeforeWebsocketCallable
from .typing import FilePath
from .typing import TeardownCallable
from .typing import WebsocketCallable
from .typing import WhileServingCallable

if t.TYPE_CHECKING:
    from .wrappers import Response

T_after_serving = t.TypeVar("T_after_serving", bound=AfterServingCallable)
T_after_websocket = t.TypeVar("T_after_websocket", bound=AfterWebsocketCallable)
T_before_serving = t.TypeVar("T_before_serving", bound=BeforeServingCallable)
T_before_websocket = t.TypeVar("T_before_websocket", bound=BeforeWebsocketCallable)
T_teardown = t.TypeVar("T_teardown", bound=TeardownCallable)
T_websocket = t.TypeVar("T_websocket", bound=WebsocketCallable)
T_while_serving = t.TypeVar("T_while_serving", bound=WhileServingCallable)


class Blueprint(SansioBlueprint):
    """A blueprint is a collection of application properties.

    The application properties include routes, error handlers, and
    before and after request functions. It is useful to produce
    modular code as it allows the properties to be defined in a
    blueprint thereby deferring the addition of these properties to the
    app.
    """

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)

        self.cli = AppGroup()
        self.cli.name = self.name

        self.after_websocket_funcs: dict[
            AppOrBlueprintKey, list[AfterWebsocketCallable]
        ] = defaultdict(list)
        self.before_websocket_funcs: dict[
            AppOrBlueprintKey, list[BeforeWebsocketCallable]
        ] = defaultdict(list)
        self.teardown_websocket_funcs: dict[
            AppOrBlueprintKey, list[TeardownCallable]
        ] = defaultdict(list)

    def get_send_file_max_age(self, filename: str | None) -> int | None:
        """Used by :func:`send_file` to determine the ``max_age`` cache
        value for a given file path if it wasn't passed.

        By default, this returns :data:`SEND_FILE_MAX_AGE_DEFAULT` from
        the configuration of :data:`~flask.current_app`. This defaults
        to ``None``, which tells the browser to use conditional requests
        instead of a timed cache, which is usually preferable.

        Note this is a duplicate of the same method in the Quart
        class.

        """
        value = current_app.config["SEND_FILE_MAX_AGE_DEFAULT"]

        if value is None:
            return None

        if isinstance(value, timedelta):
            return int(value.total_seconds())

        return value
        return None

    async def send_static_file(self, filename: str) -> Response:
        if not self.has_static_folder:
            raise RuntimeError("No static folder for this object")
        return await send_from_directory(self.static_folder, filename)

    async def open_resource(
        self,
        path: FilePath,
        mode: str = "rb",
    ) -> AiofilesContextManager:
        """Open a file for reading.

        Use as

        .. code-block:: python

            async with await app.open_resource(path) as file_:
                await file_.read()
        """
        if mode not in {"r", "rb", "rt"}:
            raise ValueError("Files can only be opened for reading")

        return async_open(os.path.join(self.root_path, path), mode)  # type: ignore

    def websocket(
        self,
        rule: str,
        **options: t.Any,
    ) -> t.Callable[[T_websocket], T_websocket]:
        """Add a websocket to the application.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.websocket('/')
            async def websocket_route():
                ...

        Arguments:
            rule: The path to route on, should start with a ``/``.
            endpoint: Optional endpoint name, if not present the
                function name is used.
            defaults: A dictionary of variables to provide automatically, use
                to provide a simpler default path for a route, e.g. to allow
                for ``/book`` rather than ``/book/0``,

                .. code-block:: python

                    @app.websocket('/book', defaults={'page': 0})
                    @app.websocket('/book/<int:page>')
                    def book(page):
                        ...

            host: The full host name for this route (should include subdomain
                if needed) - cannot be used with subdomain.
            subdomain: A subdomain for this specific route.
            strict_slashes: Strictly match the trailing slash present in the
                path. Will redirect a leaf (no slash) to a branch (with slash).
        """

        def decorator(func: T_websocket) -> T_websocket:
            endpoint = options.pop("endpoint", None)
            self.add_websocket(
                rule,
                endpoint,
                func,
                **options,
            )
            return func

        return decorator

    def add_websocket(
        self,
        rule: str,
        endpoint: str | None = None,
        view_func: WebsocketCallable | None = None,
        **options: t.Any,
    ) -> None:
        """Add a websocket url rule to the application.

        This is designed to be used on the application directly. An
        example usage,

        .. code-block:: python

            def websocket_route():
                ...

            app.add_websocket('/', websocket_route)

        Arguments:
            rule: The path to route on, should start with a ``/``.
            endpoint: Optional endpoint name, if not present the
                function name is used.
            view_func: Callable that returns a response.
            defaults: A dictionary of variables to provide automatically, use
                to provide a simpler default path for a route, e.g. to allow
                for ``/book`` rather than ``/book/0``,

                .. code-block:: python

                    @app.websocket('/book', defaults={'page': 0})
                    @app.websocket('/book/<int:page>')
                    def book(page):
                        ...

            host: The full host name for this route (should include subdomain
                if needed) - cannot be used with subdomain.
            subdomain: A subdomain for this specific route.
            strict_slashes: Strictly match the trailing slash present in the
                path. Will redirect a leaf (no slash) to a branch (with slash).
        """
        return self.add_url_rule(
            rule,
            endpoint,
            view_func,
            methods={"GET"},
            websocket=True,
            **options,
        )

    @setupmethod
    def before_websocket(
        self,
        func: T_before_websocket,
    ) -> T_before_websocket:
        """Add a before websocket function.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.before_websocket
            async def func():
                ...

        Arguments:
            func: The before websocket function itself.
        """
        self.before_websocket_funcs[None].append(func)
        return func

    @setupmethod
    def after_websocket(
        self,
        func: T_after_websocket,
    ) -> T_after_websocket:
        """Add an after websocket function.

        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,

        .. code-block:: python

            @app.after_websocket
            async def func(response):
                return response

        Arguments:
            func: The after websocket function itself.
        """
        self.after_websocket_funcs[None].append(func)
        return func

    @setupmethod
    def teardown_websocket(
        self,
        func: T_teardown,
    ) -> T_teardown:
        """Add a teardown websocket function.
        This is designed to be used as a decorator, if used to
        decorate a synchronous function, the function will be wrapped
        in :func:`~quart.utils.run_sync` and run in a thread executor
        (with the wrapped function returned). An example usage,
        .. code-block:: python
            @app.teardown_websocket
            async def func():
                ...
        Arguments:
            func: The teardown websocket function itself.
            name: Optional blueprint key name.
        """
        self.teardown_websocket_funcs[None].append(func)
        return func

    @setupmethod
    def before_app_websocket(self, func: T_before_websocket) -> T_before_websocket:
        """Add a before websocket to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.before_websocket`. It applies to all requests to the
        app this blueprint is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_app_websocket
            def before():
                ...

        """
        self.record_once(lambda state: state.app.before_websocket(func))  # type: ignore
        return func

    @setupmethod
    def before_app_serving(self, func: T_before_serving) -> T_before_serving:
        """Add a before serving to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.before_serving`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_app_serving
            def before():
                ...

        """
        self.record_once(lambda state: state.app.before_serving(func))  # type: ignore
        return func

    @setupmethod
    def after_app_websocket(self, func: T_after_websocket) -> T_after_websocket:
        """Add an after websocket function to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.after_websocket`. It applies to all requests to the
        ppe this blueprint is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.after_app_websocket
            def after():
                ...
        """
        self.record_once(lambda state: state.app.after_websocket(func))  # type: ignore
        return func

    @setupmethod
    def after_app_serving(self, func: T_after_serving) -> T_after_serving:
        """Add an after serving function to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.after_serving`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.after_app_serving
            def after():
                ...
        """
        self.record_once(lambda state: state.app.after_serving(func))  # type: ignore[attr-defined]
        return func

    @setupmethod
    def while_app_serving(self, func: T_while_serving) -> T_while_serving:
        """Add a while serving function to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.while_serving`. An example usage,

        .. code-block:: python

            @blueprint.while_serving
            async def func():
                ...  # Startup
                yield
                ...  # Shutdown

        """
        self.record_once(lambda state: state.app.while_serving(func))  # type: ignore[attr-defined]
        return func

    @setupmethod
    def teardown_app_websocket(self, func: T_teardown) -> T_teardown:
        """Add a teardown websocket function to the app.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.teardown_websocket`. It applies
        to all requests to the app this blueprint is registered on. An
        example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.teardown_app_websocket
            def teardown():
                ...
        """
        self.record_once(lambda state: state.app.teardown_websocket(func))  # type: ignore
        return func

    def _merge_blueprint_funcs(self, app: App, name: str) -> None:
        super()._merge_blueprint_funcs(app, name)

        def extend(bp_dict: dict, parent_dict: dict) -> None:
            for key, values in bp_dict.items():
                key = name if key is None else f"{name}.{key}"
                parent_dict[key].extend(values)

        for key, value in self.error_handler_spec.items():
            key = name if key is None else f"{name}.{key}"
            value = defaultdict(
                dict,
                {
                    code: {exc_class: func for exc_class, func in code_values.items()}
                    for code, code_values in value.items()
                },
            )
            app.error_handler_spec[key] = value

        extend(self.before_websocket_funcs, app.before_websocket_funcs)  # type: ignore
        extend(self.after_websocket_funcs, app.after_websocket_funcs)  # type: ignore
