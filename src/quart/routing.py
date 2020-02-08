import warnings
from typing import Iterable, Optional

from werkzeug.routing import Map, MapAdapter, Rule

from .wrappers.base import BaseRequestWebsocket


class QuartRule(Rule):
    def __init__(
        self,
        string: str,
        defaults: Optional[dict] = None,
        subdomain: Optional[str] = None,
        methods: Optional[Iterable[str]] = None,
        endpoint: Optional[str] = None,
        strict_slashes: Optional[bool] = None,
        merge_slashes: Optional[bool] = None,
        host: Optional[str] = None,
        websocket: bool = False,
        provide_automatic_options: bool = False,
    ) -> None:
        super().__init__(  # type: ignore
            string,
            defaults=defaults,
            subdomain=subdomain,
            methods=methods,
            endpoint=endpoint,
            strict_slashes=strict_slashes,
            host=host,
            websocket=websocket,
        )
        self.provide_automatic_options = provide_automatic_options


class QuartMap(Map):
    def bind_to_request(
        self, request: BaseRequestWebsocket, subdomain: Optional[str], server_name: Optional[str],
    ) -> MapAdapter:
        host = server_name or request.host
        if request.scheme in {"http", "ws"} and host.endswith(":80"):
            host = host[:-3]
        elif request.scheme in {"https", "wss"} and host.endswith(":443"):
            host = host[:-4]

        if subdomain is None and not self.host_matching:
            request_host_parts = request.host.split(".")
            config_host_parts = host.split(".")
            offset = -len(config_host_parts)

            if request_host_parts[offset:] != config_host_parts:
                warnings.warn(
                    f"Current server name '{request.host}' doesn't match configured"
                    f" server name '{host}'",
                    stacklevel=2,
                )
                subdomain = "<invalid>"
            else:
                subdomain = ".".join(filter(None, request_host_parts[:offset]))

        return super().bind(
            host,
            request.root_path,
            subdomain,
            request.scheme,
            request.method,
            request.path,
            request.query_string,
        )
