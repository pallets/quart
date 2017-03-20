from functools import update_wrapper
from typing import Callable, List, Optional, TYPE_CHECKING, Union

from .static import PackageStatic

if TYPE_CHECKING:
    from .app import Quart  # noqa

DeferedSetupFunction = Callable[['BlueprintSetupState'], None]


class Blueprint(PackageStatic):

    def __init__(
            self,
            name: str,
            import_name: str,
            static_folder: Optional[str]=None,
            static_url_path: Optional[str]=None,
            template_folder: Optional[str]=None,
            url_prefix: Optional[str]=None,
            root_path: Optional[str]=None,
    ) -> None:
        super().__init__(import_name, template_folder, root_path)
        self.name = name
        self.url_prefix = url_prefix
        self.deferred_functions: List[DeferedSetupFunction] = []

    def route(
            self,
            path: str,
            methods: List[str]=['GET'],
            *,
            provide_automatic_options: bool=True
    ) -> Callable:

        def decorator(func: Callable) -> Callable:
            self.add_url_rule(
                path, func, methods, provide_automatic_options=provide_automatic_options,
            )
            return func
        return decorator

    def add_url_rule(
            self,
            path: str,
            func: Callable,
            methods: List[str]=['GET'],
            endpoint: Optional[str]=None,
            *,
            provide_automatic_options: bool=True
    ) -> None:
        endpoint = endpoint or func.__name__
        if '.' in endpoint:
            raise ValueError('Blueprint endpoints should not contain periods')
        self.record(
            lambda state: state.add_url_rule(
                path, func, methods, endpoint, provide_automatic_options=provide_automatic_options,
            ),
        )

    def before_request(self, func: Callable) -> Callable:
        self.record_once(lambda state: state.app.before_request(func, self.name))
        return func

    def before_app_request(self, func: Callable) -> Callable:
        self.record_once(lambda state: state.app.before_request(func))
        return func

    def before_app_first_request(self, func: Callable) -> Callable:
        self.record_once(lambda state: state.app.before_first_request(func))
        return func

    def after_request(self, func: Callable) -> Callable:
        self.record_once(lambda state: state.app.after_request(func, self.name))
        return func

    def after_app_request(self, func: Callable) -> Callable:
        self.record_once(lambda state: state.app.after_request(func))
        return func

    def errorhandler(self, error: Union[Exception, int]) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.register_error_handler(error, func)
            return func
        return decorator

    def app_errorhandler(self, error: Union[Exception, int]) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.record_once(lambda state: state.app.register_error_handler(error, func))
            return func
        return decorator

    def register_error_handler(self, error: Union[Exception, int], func: Callable) -> None:
        self.record_once(lambda state: state.app.register_error_handler(error, func, self.name))

    def context_processor(self, func: Callable) -> Callable:
        self.record_once(lambda state: state.app.context_processor(func, self.name))
        return func

    def app_context_processor(self, func: Callable) -> Callable:
        self.record_once(lambda state: state.app.context_processor(func))
        return func

    def record(self, func: DeferedSetupFunction) -> None:
        self.deferred_functions.append(func)

    def record_once(self, func: DeferedSetupFunction) -> None:
        def wrapper(state: 'BlueprintSetupState') -> None:
            if state.first_registration:
                func(state)
        self.record(update_wrapper(wrapper, func))  # type: ignore

    def register(
            self,
            app: 'Quart',
            first_registration: bool,
            *,
            url_prefix: Optional[str]=None
    ) -> None:
        state = self.make_setup_state(app, first_registration, url_prefix=url_prefix)
        for func in self.deferred_functions:
            func(state)

    def make_setup_state(
            self,
            app: 'Quart',
            first_registration: bool,
            *,
            url_prefix: Optional[str]=None
    ) -> 'BlueprintSetupState':
        return BlueprintSetupState(self, app, first_registration, url_prefix=url_prefix)


class BlueprintSetupState:

    def __init__(
            self,
            blueprint: Blueprint,
            app: 'Quart',
            first_registration: bool,
            *,
            url_prefix: Optional[str]=None
    ) -> None:
        self.blueprint = blueprint
        self.app = app
        self.url_prefix = url_prefix or self.blueprint.url_prefix
        self.first_registration = first_registration

    def add_url_rule(
            self,
            path: str,
            func: Callable,
            methods: List[str]=['GET'],
            endpoint: Optional[str]=None,
            *,
            provide_automatic_options: bool=True
    ) -> None:
        if self.url_prefix is not None:
            path = "{}{}".format(self.url_prefix, path)
        endpoint = "{}.{}".format(self.blueprint.name, endpoint)
        self.app.add_url_rule(
            path, func, methods, endpoint, provide_automatic_options=provide_automatic_options,
        )
