from functools import update_wrapper
from json import JSONDecoder, JSONEncoder
from typing import Callable, Iterable, List, Optional, TYPE_CHECKING, Union

from .static import PackageStatic

if TYPE_CHECKING:
    from .app import Quart  # noqa

DeferedSetupFunction = Callable[['BlueprintSetupState'], Callable]


class Blueprint(PackageStatic):
    """A blueprint is a collection of application properties.

    The application properties include routes, error handlers, and
    before and after request functions. It is useful to produce
    modular code as it allows the properties to be defined in a
    blueprint thereby defering the addition of these properties to the
    app.

    Attributes:
        json_decoder: The decoder to use for routes in this blueprint,
            the default, None, indicates that the app encoder should be
            used.
        json_encoder: The encoder to use for routes in this blueprint,
            the default, None, indicates that the app encoder should be
            used.
        url_prefix: An additional prefix to every route rule in the
            blueprint.
    """

    json_decoder: Optional[JSONDecoder] = None
    json_encoder: Optional[JSONEncoder] = None

    def __init__(
            self,
            name: str,
            import_name: str,
            static_folder: Optional[str]=None,
            static_url_path: Optional[str]=None,
            template_folder: Optional[str]=None,
            url_prefix: Optional[str]=None,
            subdomain: Optional[str]=None,
            root_path: Optional[str]=None,
    ) -> None:
        super().__init__(import_name, template_folder, root_path)
        self.name = name
        self.url_prefix = url_prefix
        self.deferred_functions: List[DeferedSetupFunction] = []
        self.subdomain = subdomain

    def route(
            self,
            path: str,
            methods: Optional[List[str]]=None,
            endpoint: Optional[str]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            provide_automatic_options: bool=True,
            strict_slashes: bool=True,
    ) -> Callable:
        """Add a route to the blueprint.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.route`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.route('/')
            def route():
                ...
        """
        def decorator(func: Callable) -> Callable:
            self.add_url_rule(
                path, endpoint, func, methods, defaults=defaults, host=host, subdomain=subdomain,
                provide_automatic_options=provide_automatic_options, strict_slashes=strict_slashes,
            )
            return func
        return decorator

    def add_url_rule(
            self,
            path: str,
            endpoint: Optional[str]=None,
            view_func: Optional[Callable]=None,
            methods: Optional[Iterable[str]]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            provide_automatic_options: bool=True,
            is_websocket: bool=False,
            strict_slashes: bool=True,
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
        endpoint = endpoint or view_func.__name__
        if '.' in endpoint:
            raise ValueError('Blueprint endpoints should not contain periods')
        self.record(
            lambda state: state.add_url_rule(
                path, endpoint, view_func, methods, defaults, host, self.subdomain,
                provide_automatic_options=provide_automatic_options, is_websocket=is_websocket,
                strict_slashes=strict_slashes,
            ),
        )

    def websocket(
            self,
            path: str,
            endpoint: Optional[str]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            strict_slashes: bool=True,
    ) -> Callable:
        """Add a websocket to the blueprint.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.websocket`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.websocket('/')
            async def route():
                ...
        """
        def decorator(func: Callable) -> Callable:
            self.add_websocket(
                path, endpoint, func, defaults=defaults, host=host, subdomain=subdomain,
                strict_slashes=strict_slashes,
            )
            return func
        return decorator

    def add_websocket(
            self,
            path: str,
            endpoint: Optional[str]=None,
            view_func: Optional[Callable]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            strict_slashes: bool=True,
    ) -> None:
        """Add a websocket rule to the blueprint.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_websocket`. An example usage,

        .. code-block:: python

            def route():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_websocket('/', route)
        """
        return self.add_url_rule(
            path, endpoint, view_func, {'GET'}, defaults=defaults, host=host, subdomain=subdomain,
            provide_automatic_options=False, is_websocket=True, strict_slashes=strict_slashes,
        )

    def endpoint(self, endpoint: str) -> Callable:
        """Add an endpoint to the blueprint.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.endpoint`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.endpoint('index')
            def index():
                ...
        """
        def decorator(func: Callable) -> Callable:
            self.record_once(lambda state: state.register_endpoint(endpoint, func))
            return func
        return decorator

    def app_template_filter(self, name: Optional[str]=None) -> Callable:
        """Add an application wide template filter.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_filter`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_filter()
            def filter(value):
                ...
        """
        def decorator(func: Callable) -> Callable:
            self.add_app_template_filter(func, name=name)
            return func
        return decorator

    def add_app_template_filter(self, func: Callable, name: Optional[str]=None) -> None:
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

    def app_template_test(self, name: Optional[str]=None) -> Callable:
        """Add an application wide template test.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_test`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_test()
            def test(value):
                ...
        """
        def decorator(func: Callable) -> Callable:
            self.add_app_template_test(func, name=name)
            return func
        return decorator

    def add_app_template_test(self, func: Callable, name: Optional[str]=None) -> None:
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

    def app_template_global(self, name: Optional[str]=None) -> Callable:
        """Add an application wide template global.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_global`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_global()
            def global(value):
                ...
        """
        def decorator(func: Callable) -> Callable:
            self.add_app_template_global(func, name=name)
            return func
        return decorator

    def add_app_template_global(self, func: Callable, name: Optional[str]=None) -> None:
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

    def before_request(self, func: Callable) -> Callable:
        """Add a before request function to the Blueprint.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.before_request`. It applies only to requests that
        are routed to an endpoint in this blueprint. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_request
            def before():
                ...
        """
        self.record_once(lambda state: state.app.before_request(func, self.name))
        return func

    def before_websocket(self, func: Callable) -> Callable:
        """Add a before request websocket to the Blueprint.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.before_websocket`. It applies
        only to requests that are routed to an endpoint in this
        blueprint. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_websocket
            def before():
                ...

        """
        self.record_once(lambda state: state.app.before_websocket(func, self.name))
        return func

    def before_app_request(self, func: Callable) -> Callable:
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

    def before_app_first_request(self, func: Callable) -> Callable:
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

    def after_request(self, func: Callable) -> Callable:
        """Add an after request function to the Blueprint.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.after_request`. It applies only to requests that
        are routed to an endpoint in this blueprint. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.after_request
            def after():
                ...
        """
        self.record_once(lambda state: state.app.after_request(func, self.name))
        return func

    def after_websocket(self, func: Callable) -> Callable:
        """Add an after websocket function to the Blueprint.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.after_websocket`. It applies
        only to requests that are routed to an endpoint in this
        blueprint. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.after_websocket
            def after():
                ...
        """
        self.record_once(lambda state: state.app.after_websocket(func, self.name))
        return func

    def after_app_request(self, func: Callable) -> Callable:
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

    def teardown_request(self, func: Callable) -> Callable:
        """Add a teardown request function to the Blueprint.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.teardown_request`. It applies only to requests that
        are routed to an endpoint in this blueprint. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.teardown_request
            def teardown():
                ...
        """
        self.record_once(lambda state: state.app.teardown_request(func, self.name))
        return func

    def teardown_websocket(self, func: Callable) -> Callable:
        """Add a teardown websocket function to the Blueprint.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.teardown_websocket`. It
        applies only to requests that are routed to an endpoint in
        this blueprint. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.teardown_websocket
            def teardown():
                ...

        """
        self.record_once(lambda state: state.app.teardown_websocket(func, self.name))
        return func

    def teardown_app_request(self, func: Callable) -> Callable:
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

    def errorhandler(self, error: Union[Exception, int]) -> Callable:
        """Add an error handler function to the Blueprint.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.errorhandler`. It applies
        only to errors that originate in routes in this blueprint. An
        example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.errorhandler(404)
            def not_found():
                ...

        """
        def decorator(func: Callable) -> Callable:
            self.register_error_handler(error, func)
            return func
        return decorator

    def app_errorhandler(self, error: Union[Exception, int]) -> Callable:
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
        def decorator(func: Callable) -> Callable:
            self.record_once(lambda state: state.app.register_error_handler(error, func))
            return func
        return decorator

    def register_error_handler(self, error: Union[Exception, int], func: Callable) -> None:
        """Add an error handler function to the blueprint.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.register_error_handler`. An example usage,

        .. code-block:: python

            def not_found():
                ...

            blueprint = Blueprint(__name__)
            blueprint.register_error_handler(404, not_found)
        """
        self.record_once(lambda state: state.app.register_error_handler(error, func, self.name))

    def context_processor(self, func: Callable) -> Callable:
        """Add a context processor function to this blueprint.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.context_processor`. This will
        add context to all templates rendered in this blueprint's
        routes. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.context_processor
            def processor():
                ...
        """
        self.record_once(lambda state: state.app.context_processor(func, self.name))
        return func

    def app_context_processor(self, func: Callable) -> Callable:
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

    def url_value_preprocessor(self, func: Callable) -> Callable:
        """Add a url value preprocessor.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.url_value_preprocessor`. This
        will apply to urls in this blueprint. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.url_value_preprocessor
            def processor(endpoint, view_args):
                ...

        """
        self.record_once(lambda state: state.app.url_value_preprocessor(func, self.name))
        return func

    def app_url_value_preprocessor(self, func: Callable) -> Callable:
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

    def url_defaults(self, func: Callable) -> Callable:
        """Add a url default preprocessor.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.url_defaults`. This will
        apply to urls in this blueprint. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.url_defaults
            def default(endpoint, values):
                ...

        """
        self.record_once(lambda state: state.app.url_defaults(func, self.name))
        return func

    def app_url_defaults(self, func: Callable) -> Callable:
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

    def record(self, func: DeferedSetupFunction) -> None:
        """Used to register a deferred action."""
        self.deferred_functions.append(func)

    def record_once(self, func: DeferedSetupFunction) -> None:
        """Used to register a deferred action that happens only once."""
        def wrapper(state: 'BlueprintSetupState') -> None:
            if state.first_registration:
                func(state)
        self.record(update_wrapper(wrapper, func))  # type: ignore

    def register(
            self,
            app: 'Quart',
            first_registration: bool,
            *,
            url_prefix: Optional[str]=None,
    ) -> None:
        """Register this blueprint on the app given."""
        state = self.make_setup_state(app, first_registration, url_prefix=url_prefix)
        for func in self.deferred_functions:
            func(state)

    def make_setup_state(
            self,
            app: 'Quart',
            first_registration: bool,
            *,
            url_prefix: Optional[str]=None,
    ) -> 'BlueprintSetupState':
        """Return a blueprint setup state instance.

        Arguments:
            first_registration: True if this is the first registration
                of this blueprint on the app.
            url_prefix: An optional prefix to all rules
        """
        return BlueprintSetupState(self, app, first_registration, url_prefix=url_prefix)


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
            self,
            blueprint: Blueprint,
            app: 'Quart',
            first_registration: bool,
            *,
            url_prefix: Optional[str]=None,
    ) -> None:
        self.blueprint = blueprint
        self.app = app
        self.url_prefix = url_prefix or self.blueprint.url_prefix
        self.first_registration = first_registration

    def add_url_rule(
            self,
            path: str,
            endpoint: Optional[str]=None,
            view_func: Optional[Callable]=None,
            methods: Optional[Iterable[str]]=None,
            defaults: Optional[dict]=None,
            host: Optional[str]=None,
            subdomain: Optional[str]=None,
            *,
            provide_automatic_options: bool=True,
            is_websocket: bool=False,
            strict_slashes: bool=True,
    ) -> None:
        if self.url_prefix is not None:
            path = f"{self.url_prefix}{path}"
        endpoint = f"{self.blueprint.name}.{endpoint}"
        self.app.add_url_rule(
            path, endpoint, view_func, methods, defaults, host=host, subdomain=subdomain,
            provide_automatic_options=provide_automatic_options, is_websocket=is_websocket,
            strict_slashes=strict_slashes,
        )

    def register_endpoint(self, endpoint: str, func: Callable) -> None:
        self.app.view_functions[endpoint] = func

    def register_template_filter(self, func: Callable, name: Optional[str]) -> None:
        self.app.add_template_filter(func, name)

    def register_template_test(self, func: Callable, name: Optional[str]) -> None:
        self.app.add_template_test(func, name)

    def register_template_global(self, func: Callable, name: Optional[str]) -> None:
        self.app.add_template_global(func, name)
