from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING

from hypercorn.typing import WWWScope
from werkzeug.datastructures import Headers
from werkzeug.sansio.request import Request as SansIORequest

from .. import json

if TYPE_CHECKING:
    from ..routing import QuartRule  # noqa


class BaseRequestWebsocket(SansIORequest):
    """This class is the basis for Requests and websockets..

    Attributes:
        json_module: A custom json decoding/encoding module, it should
            have `dump`, `dumps`, `load`, and `loads` methods
        routing_exception: If an exception is raised during the route
            matching it will be stored here.
        url_rule: The rule that this request has been matched too.
        view_args: The keyword arguments for the view from the route
            matching.
    """

    json_module: json.provider.JSONProvider = json  # type: ignore
    routing_exception: Exception | None = None
    url_rule: QuartRule | None = None
    view_args: dict[str, Any] | None = None

    def __init__(
        self,
        method: str,
        scheme: str,
        path: str,
        query_string: bytes,
        headers: Headers,
        root_path: str,
        http_version: str,
        scope: WWWScope,
    ) -> None:
        """Create a request or websocket base object.

        Arguments:
            method: The HTTP verb.
            scheme: The scheme used for the request.
            path: The full unquoted path of the request.
            query_string: The raw bytes for the query string part.
            headers: The request headers.
            root_path: The root path that should be prepended to all
                routes.
            http_version: The HTTP version of the request.
            scope: Underlying ASGI scope dictionary.

        Attributes:
            args: The query string arguments.
            scheme: The URL scheme, http or https.
        """
        super().__init__(
            method,
            scheme,
            scope.get("server"),
            root_path,
            path,
            query_string,
            headers,
            headers.get("Remote-Addr"),
        )
        self.http_version = http_version
        self.scope = scope

    @property
    def endpoint(self) -> str | None:
        """Returns the corresponding endpoint matched for this request.

        This can be None if the request has not been matched with a
        rule.
        """
        if self.url_rule is not None:
            return self.url_rule.endpoint
        else:
            return None

    @property
    def blueprint(self) -> str | None:
        """Returns the blueprint the matched endpoint belongs to.

        This can be None if the request has not been matched or the
        endpoint is not in a blueprint.
        """
        if self.endpoint is not None and "." in self.endpoint:
            return self.endpoint.rsplit(".", 1)[0]
        else:
            return None

    @property
    def blueprints(self) -> list[str]:
        """Return the names of the current blueprints.
        The returned list is ordered from the current blueprint,
        upwards through parent blueprints.
        """
        # Avoid circular import
        from ..helpers import _split_blueprint_path

        if self.blueprint is not None:
            return _split_blueprint_path(self.blueprint)
        else:
            return []

    @property
    def script_root(self) -> str:
        return self.root_path

    @property
    def url_root(self) -> str:
        return self.root_url
