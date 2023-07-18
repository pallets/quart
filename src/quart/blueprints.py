from __future__ import annotations

from collections import defaultdict
from functools import update_wrapper
from typing import Any, Callable, Iterable, TYPE_CHECKING, TypeVar

from .scaffold import _endpoint_from_view_func, Scaffold, setupmethod
from .typing import (
    AfterRequestCallable,
    AfterServingCallable,
    AfterWebsocketCallable,
    BeforeFirstRequestCallable,
    BeforeRequestCallable,
    BeforeServingCallable,
    BeforeWebsocketCallable,
    ErrorHandlerCallable,
    RouteCallable,
    TeardownCallable,
    TemplateContextProcessorCallable,
    TemplateFilterCallable,
    TemplateGlobalCallable,
    TemplateTestCallable,
    URLDefaultCallable,
    URLValuePreprocessorCallable,
    WebsocketCallable,
    WhileServingCallable,
)

if TYPE_CHECKING:
    from .app import Quart  # noqa

DeferredSetupFunction = Callable[["BlueprintSetupState"], Callable]
T_after_request = TypeVar("T_after_request", bound=AfterRequestCallable)
T_after_websocket = TypeVar("T_after_websocket", bound=AfterWebsocketCallable)
T_after_serving = TypeVar("T_after_serving", bound=AfterServingCallable)
T_before_first_request = TypeVar("T_before_first_request", bound=BeforeFirstRequestCallable)
T_before_request = TypeVar("T_before_request", bound=BeforeRequestCallable)
T_before_websocket = TypeVar("T_before_websocket", bound=BeforeWebsocketCallable)
T_before_serving = TypeVar("T_before_serving", bound=BeforeServingCallable)
T_error_handler = TypeVar("T_error_handler", bound=ErrorHandlerCallable)
T_teardown = TypeVar("T_teardown", bound=TeardownCallable)
T_template_context_processor = TypeVar(
    "T_template_context_processor", bound=TemplateContextProcessorCallable
)
T_template_filter = TypeVar("T_template_filter", bound=TemplateFilterCallable)
T_template_global = TypeVar("T_template_global", bound=TemplateGlobalCallable)
T_template_test = TypeVar("T_template_test", bound=TemplateTestCallable)
T_url_defaults = TypeVar("T_url_defaults", bound=URLDefaultCallable)
T_url_value_preprocessor = TypeVar("T_url_value_preprocessor", bound=URLValuePreprocessorCallable)
T_while_serving = TypeVar("T_while_serving", bound=WhileServingCallable)


class Blueprint(Scaffold):
    """A blueprint is a collection of application properties.

    The application properties include routes, error handlers, and
    before and after request functions. It is useful to produce
    modular code as it allows the properties to be defined in a
    blueprint thereby deferring the addition of these properties to the
    app.

    Attributes:
        url_prefix: An additional prefix to every route rule in the
            blueprint.
    """

    warn_on_modifications = False
    _got_registered_once = False

    def __init__(
        self,
        name: str,
        import_name: str,
        static_folder: str | None = None,
        static_url_path: str | None = None,
        template_folder: str | None = None,
        url_prefix: str | None = None,
        subdomain: str | None = None,
        url_defaults: dict | None = None,
        root_path: str | None = None,
        cli_group: str | None = Ellipsis,  # type: ignore
    ) -> None:
        super().__init__(import_name, static_folder, static_url_path, template_folder, root_path)

        if "." in name:
            raise ValueError("Blueprint names may not contain dot '.' characters.")

        self.name = name
        self.url_prefix = url_prefix
        self.deferred_functions: list[DeferredSetupFunction] = []
        self.subdomain = subdomain
        if url_defaults is None:
            url_defaults = {}
        self.url_values_defaults = url_defaults
        self.cli_group = cli_group
        self._blueprints: list[tuple[Blueprint, dict]] = []

    def _check_setup_finished(self, f_name: str) -> None:
        if self._got_registered_once:
            raise AssertionError(
                f"The setup method '{f_name}' can no longer be called on"
                f" the blueprint '{self.name}'. It has already been"
                " registered at least once, any changes will not be"
                " applied consistently.\n"
                "Make sure all imports, decorators, functions, etc."
                " needed to set up the blueprint are done before"
                " registering it.\n"
            )

    @setupmethod
    def add_url_rule(
        self,
        rule: str,
        endpoint: str | None = None,
        view_func: RouteCallable | WebsocketCallable | None = None,
        provide_automatic_options: bool | None = None,
        *,
        methods: Iterable[str] | None = None,
        defaults: dict | None = None,
        host: str | None = None,
        subdomain: str | None = None,
        is_websocket: bool = False,
        strict_slashes: bool | None = None,
        merge_slashes: bool | None = None,
    ) -> None:
        """Add a route/url rule to the blueprint.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_url_rule`. An example usage,

        .. code-block:: python

            def route():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_url_rule('/', route)
        """
        endpoint = endpoint or _endpoint_from_view_func(view_func)
        if "." in endpoint:
            raise ValueError("Blueprint endpoints should not contain periods")
        self.record(
            lambda state: state.add_url_rule(
                rule,
                endpoint,
                view_func,
                provide_automatic_options=provide_automatic_options,
                methods=methods,
                defaults=defaults,
                host=host,
                subdomain=subdomain,
                is_websocket=is_websocket,
                strict_slashes=strict_slashes,
                merge_slashes=merge_slashes,
            )
        )

    @setupmethod
    def app_template_filter(
        self, name: str | None = None
    ) -> Callable[[T_template_filter], T_template_filter]:
        """Add an application wide template filter.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_filter`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_filter()
            def filter(value):
                ...
        """

        def decorator(func: T_template_filter) -> T_template_filter:
            self.add_app_template_filter(func, name=name)
            return func

        return decorator

    @setupmethod
    def add_app_template_filter(
        self, func: TemplateFilterCallable, name: str | None = None
    ) -> None:
        """Add an application wide template filter.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_template_filter`. An example usage,

        .. code-block:: python

            def filter():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_app_template_filter(filter)
        """
        self.record_once(lambda state: state.register_template_filter(func, name))

    @setupmethod
    def app_template_test(
        self, name: str | None = None
    ) -> Callable[[T_template_test], T_template_test]:
        """Add an application wide template test.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_test`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_test()
            def test(value):
                ...
        """

        def decorator(func: T_template_test) -> T_template_test:
            self.add_app_template_test(func, name=name)
            return func

        return decorator

    @setupmethod
    def add_app_template_test(self, func: TemplateTestCallable, name: str | None = None) -> None:
        """Add an application wide template test.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_template_test`. An example usage,

        .. code-block:: python

            def test():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_app_template_test(test)
        """
        self.record_once(lambda state: state.register_template_test(func, name))

    @setupmethod
    def app_template_global(
        self, name: str | None = None
    ) -> Callable[[T_template_global], T_template_global]:
        """Add an application wide template global.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_global`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_global()
            def global(value):
                ...
        """

        def decorator(func: T_template_global) -> T_template_global:
            self.add_app_template_global(func, name=name)
            return func

        return decorator

    @setupmethod
    def add_app_template_global(
        self, func: TemplateGlobalCallable, name: str | None = None
    ) -> None:
        """Add an application wide template global.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_template_global`. An example usage,

        .. code-block:: python

            def global():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_app_template_global(global)
        """
        self.record_once(lambda state: state.register_template_global(func, name))

    @setupmethod
    def before_app_request(self, func: T_before_request) -> T_before_request:
        """Add a before request function to the app.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.before_request`. It applies to all requests to the
        app this blueprint is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_app_request
            def before():
                ...
        """
        self.record_once(lambda state: state.app.before_request(func))
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
        self.record_once(lambda state: state.app.before_websocket(func))
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
        self.record_once(lambda state: state.app.before_serving(func))
        return func

    @setupmethod
    def before_app_first_request(self, func: T_before_first_request) -> T_before_first_request:
        """Add a before request first function to the app.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.before_first_request`. It is
        triggered before the first request to the app this blueprint
        is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_app_first_request
            def before_first():
                ...

        """
        self.record_once(lambda state: state.app.before_first_request(func))
        return func

    @setupmethod
    def after_app_request(self, func: T_after_request) -> T_after_request:
        """Add a after request function to the app.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.after_request`. It applies to all requests to the
        app this blueprint is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.after_app_request
            def after():
                ...
        """
        self.record_once(lambda state: state.app.after_request(func))
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
        self.record_once(lambda state: state.app.after_websocket(func))
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
        self.record_once(lambda state: state.app.after_serving(func))
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
        self.record_once(lambda state: state.app.while_serving(func))
        return func

    @setupmethod
    def teardown_app_request(self, func: T_teardown) -> T_teardown:
        """Add a teardown request function to the app.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.teardown_request`. It applies
        to all requests to the app this blueprint is registered on. An
        example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.teardown_app_request
            def teardown():
                ...
        """
        self.record_once(lambda state: state.app.teardown_request(func))
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
        self.record_once(lambda state: state.app.teardown_websocket(func))
        return func

    @setupmethod
    def app_errorhandler(
        self, error: type[Exception] | int
    ) -> Callable[[T_error_handler], T_error_handler]:
        """Add an error handler function to the App.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.errorhandler`. It applies
        only to all errors. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_errorhandler(404)
            def not_found():
                ...
        """

        def decorator(func: T_error_handler) -> T_error_handler:
            self.record_once(lambda state: state.app.register_error_handler(error, func))
            return func

        return decorator

    @setupmethod
    def app_context_processor(
        self,
        func: T_template_context_processor,
    ) -> T_template_context_processor:
        """Add a context processor function to the app.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.context_processor`. This will
        add context to all templates rendered. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_context_processor
            def processor():
                ...
        """
        self.record_once(lambda state: state.app.context_processor(func))
        return func

    @setupmethod
    def app_url_value_preprocessor(
        self, func: T_url_value_preprocessor
    ) -> T_url_value_preprocessor:
        """Add a url value preprocessor.

        This is designed to be used as a decorator, and has the same
        arguments as
        :meth:`~quart.Quart.app_url_value_preprocessor`. This will
        apply to all URLs. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_url_value_preprocessor
            def processor(endpoint, view_args):
                ...

        """
        self.record_once(lambda state: state.app.url_value_preprocessor(func))
        return func

    @setupmethod
    def app_url_defaults(self, func: T_url_defaults) -> T_url_defaults:
        """Add a url default preprocessor.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.url_defaults`. This will
        apply to all urls. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_url_defaults
            def default(endpoint, values):
                ...

        """
        self.record_once(lambda state: state.app.url_defaults(func))
        return func

    @setupmethod
    def record(self, func: DeferredSetupFunction) -> None:
        """Used to register a deferred action."""
        self.deferred_functions.append(func)

    @setupmethod
    def record_once(self, func: DeferredSetupFunction) -> None:
        """Used to register a deferred action that happens only once."""

        def wrapper(state: BlueprintSetupState) -> None:
            if state.first_registration:
                func(state)

        self.record(update_wrapper(wrapper, func))

    @setupmethod
    def register_blueprint(self, blueprint: Blueprint, **options: Any) -> None:
        """Register a :class:`~quart.Blueprint` on this blueprint.

        Keyword arguments passed to this method will override the
        defaults set on the blueprint.
        """
        if blueprint is self:
            raise ValueError("Cannot register a blueprint on itself")
        self._blueprints.append((blueprint, options))

    def register(self, app: Quart, options: dict) -> None:
        """Register this blueprint on the app given.

        Arguments:
            app: The application this blueprint is being registered with.
            options: Keyword arguments forwarded from
                :meth:`~quart.Quart.register_blueprint`.
            first_registration: Whether this is the first time this
                blueprint has been registered on the application.
        """

        name = f"{options.get('name_prefix', '')}.{options.get('name', self.name)}".lstrip(".")
        if name in app.blueprints and app.blueprints[name] is not self:
            raise ValueError(
                f"Blueprint name '{self.name}' "
                f"is already registered by {app.blueprints[self.name]}. "
                "Blueprints must have unique names"
            )

        first_blueprint_registration = not any(
            blueprint is self for blueprint in app.blueprints.values()
        )
        first_name_registration = name not in app.blueprints

        app.blueprints[name] = self
        self._got_registered_once = True

        state = self.make_setup_state(app, options, first_blueprint_registration)

        if self.has_static_folder:
            state.add_url_rule(
                self.static_url_path + "/<path:filename>",
                view_func=self.send_static_file,
                endpoint="static",
            )

        if first_blueprint_registration or first_name_registration:

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

            for endpoint, func in self.view_functions.items():
                app.view_functions[endpoint] = func

            extend(self.before_request_funcs, app.before_request_funcs)
            extend(self.before_websocket_funcs, app.before_websocket_funcs)
            extend(self.after_request_funcs, app.after_request_funcs)
            extend(self.after_websocket_funcs, app.after_websocket_funcs)
            extend(
                self.teardown_request_funcs,
                app.teardown_request_funcs,
            )
            extend(
                self.teardown_websocket_funcs,
                app.teardown_websocket_funcs,
            )
            extend(self.url_default_functions, app.url_default_functions)
            extend(self.url_value_preprocessors, app.url_value_preprocessors)
            extend(self.template_context_processors, app.template_context_processors)

        for func in self.deferred_functions:
            func(state)

        cli_resolved_group = options.get("cli_group", self.cli_group)

        if self.cli.commands:
            if cli_resolved_group is None:
                app.cli.commands.update(self.cli.commands)
            elif cli_resolved_group is Ellipsis:
                self.cli.name = name
                app.cli.add_command(self.cli)
            else:
                self.cli.name = cli_resolved_group
                app.cli.add_command(self.cli)

        for blueprint, bp_options in self._blueprints:
            bp_options = bp_options.copy()
            bp_url_prefix = bp_options.get("url_prefix")
            bp_subdomain = bp_options.get("subdomain")

            if bp_subdomain is None:
                bp_subdomain = blueprint.subdomain

            if state.subdomain is not None and bp_subdomain is not None:
                bp_options["subdomain"] = bp_subdomain + "." + state.subdomain
            elif bp_subdomain is not None:
                bp_options["subdomain"] = bp_subdomain
            elif state.subdomain is not None:
                bp_options["subdomain"] = state.subdomain

            if bp_url_prefix is None:
                bp_url_prefix = blueprint.url_prefix

            if state.url_prefix is not None and bp_url_prefix is not None:
                bp_options["url_prefix"] = (
                    state.url_prefix.rstrip("/") + "/" + bp_url_prefix.lstrip("/")
                )
            elif bp_url_prefix is not None:
                bp_options["url_prefix"] = bp_url_prefix
            elif state.url_prefix is not None:
                bp_options["url_prefix"] = state.url_prefix

            bp_options["name_prefix"] = name
            blueprint.register(app, bp_options)

    def make_setup_state(
        self, app: Quart, options: dict, first_registration: bool = False
    ) -> BlueprintSetupState:
        """Return a blueprint setup state instance.

        Arguments:
            first_registration: True if this is the first registration
                of this blueprint on the app.
            options: Keyword arguments forwarded from
                :meth:`~quart.Quart.register_blueprint`.
            first_registration: Whether this is the first time this
                blueprint has been registered on the application.
        """
        return BlueprintSetupState(self, app, options, first_registration)


class BlueprintSetupState:
    """This setups the blueprint on the app.

    When used it can apply the deferred functions on the Blueprint to
    the app. Override if you wish for blueprints to have be registered
    in different ways.

    Attributes:
        first_registration: True if this is the first registration
            of this blueprint on the app.
    """

    def __init__(
        self, blueprint: Blueprint, app: Quart, options: dict, first_registration: bool
    ) -> None:
        self.blueprint = blueprint
        self.app = app
        self.options = options
        self.url_prefix = options.get("url_prefix") or blueprint.url_prefix
        self.first_registration = first_registration
        self.subdomain = options.get("subdomain") or blueprint.subdomain
        self.url_defaults = dict(self.blueprint.url_values_defaults)
        self.url_defaults.update(options.get("url_defaults", {}) or {})
        self.name = self.options.get("name", blueprint.name)
        self.name_prefix = self.options.get("name_prefix", "")

    def add_url_rule(
        self,
        path: str,
        endpoint: str | None = None,
        view_func: Callable | None = None,
        *,
        methods: Iterable[str] | None = None,
        defaults: dict | None = None,
        host: str | None = None,
        subdomain: str | None = None,
        provide_automatic_options: bool | None = None,
        is_websocket: bool = False,
        strict_slashes: bool | None = None,
        merge_slashes: bool | None = None,
    ) -> None:
        if self.url_prefix is not None:
            if path:
                path = f"{self.url_prefix.rstrip('/')}/{path.lstrip('/')}"
            else:
                path = self.url_prefix.rstrip("/")
        if subdomain is None:
            subdomain = self.subdomain
        endpoint = f"{self.name_prefix}.{self.name}.{endpoint}".lstrip(".")
        url_defaults = self.url_defaults
        if defaults is not None:
            url_defaults = {**url_defaults, **defaults}
        self.app.add_url_rule(
            path,
            endpoint,
            view_func,
            provide_automatic_options=provide_automatic_options,
            methods=methods,
            defaults=url_defaults,
            host=host,
            subdomain=subdomain,
            is_websocket=is_websocket,
            strict_slashes=strict_slashes,
            merge_slashes=merge_slashes,
        )

    def register_template_filter(self, func: TemplateFilterCallable, name: str | None) -> None:
        self.app.add_template_filter(func, name)

    def register_template_test(self, func: Callable, name: str | None) -> None:
        self.app.add_template_test(func, name)

    def register_template_global(self, func: Callable, name: str | None) -> None:
        self.app.add_template_global(func, name)


def _merge_dict_of_lists(name: str, self_dict: dict, app_dict: dict) -> None:
    for key, values in self_dict.items():
        key = name if key is None else f"{name}.{key}"
        app_dict[key].extend(values)


def _merge_dict_of_dicts(name: str, self_dict: dict, app_dict: dict) -> None:
    for key, value in self_dict.items():
        key = name if key is None else f"{name}.{key}"
        app_dict[key] = value
