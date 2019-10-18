from typing import Any, Callable, List, Optional, Tuple

from blinker import NamedSignal, Namespace

from .utils import ensure_coroutine

signals_available = True


class AsyncNamedSignal(NamedSignal):  # type: ignore
    def __init__(self, name: str, doc: Optional[str] = None) -> None:
        super().__init__(name, doc)

    async def send(self, *sender: Any, **kwargs: Any) -> List[Tuple[Callable, Any]]:
        coroutines = super().send(*sender, **kwargs)
        result: List[Tuple[Callable, Any]] = []
        for handler, coroutine in coroutines:
            result.append((handler, await coroutine))
        return result

    def connect(self, receiver: Callable, *args: Any, **kwargs: Any) -> Callable:
        handler = ensure_coroutine(receiver)
        if handler is not receiver and kwargs.get("weak", True):
            # Blinker will take a weakref to handler, which goes out
            # of scope with this method as it is a wrapper around the
            # receiver. Whereas we'd want it to go out of scope when
            # receiver does. Therefore we can place it on the receiver
            # function. (Ideally I'll think of a better way).
            receiver._quart_wrapper_func = handler  # type: ignore
        return super().connect(handler, *args, **kwargs)


class AsyncNamespace(Namespace):  # type: ignore
    def signal(self, name: str, doc: Optional[str] = None) -> AsyncNamedSignal:
        try:
            return self[name]
        except KeyError:
            return self.setdefault(name, AsyncNamedSignal(name, doc))


_signals = AsyncNamespace()

#: Called before a template is rendered, connection functions
# should have a signature of Callable[[Quart, Template, dict], None]
before_render_template = _signals.signal("before-render-template")

#: Called when a template has been rendered, connected functions
# should have a signature of Callable[[Quart, Template, dict], None]
template_rendered = _signals.signal("template-rendered")

#: Called just after the request context has been created, connected
# functions should have a signature of Callable[[Quart], None]
request_started = _signals.signal("request-started")

#: Called after a response is fully finalised, connected functions
# should have a signature of Callable[[Quart, Response], None]
request_finished = _signals.signal("request-finished")

#: Called as the request context is teared down, connected functions
# should have a signature of Callable[[Quart, Exception], None]
request_tearing_down = _signals.signal("request-tearing-down")

#: Called if there is an exception handling the request, connected
# functions should have a signature of Callable[[Quart, Exception], None]
got_request_exception = _signals.signal("got-request-exception")

#: Called just after the websocket context has been created, connected
# functions should have a signature of Callable[[Quart], None]
websocket_started = _signals.signal("websocket-started")

#: Called after a response is fully finalised, connected functions
# should have a signature of Callable[[Quart, Optional[Response]], None]
websocket_finished = _signals.signal("websocket-finished")

#: Called as the websocket context is teared down, connected functions
# should have a signature of Callable[[Quart, Exception], None]
websocket_tearing_down = _signals.signal("websocket-tearing-down")

#: Called if there is an exception handling the websocket, connected
# functions should have a signature of Callable[[Quart, Exception], None]
got_websocket_exception = _signals.signal("got-websocket-exception")

#: Called as the application context is teared down, connected functions
# should have a signature of Callable[[Quart, Exception], None]
appcontext_tearing_down = _signals.signal("appcontext-tearing-down")

#: Called when the app context is pushed, connected functions should
# have a signature of Callable[[Quart], None]
appcontext_pushed = _signals.signal("appcontext-pushed")

#: Called when the app context is poped, connected functions should
# have a signature of Callable[[Quart], None]
appcontext_popped = _signals.signal("appcontext-popped")

#: Called on a flash invocation, connection functions
# should have a signature of Callable[[Quart, str, str], None]
message_flashed = _signals.signal("message-flashed")
