from __future__ import annotations

from typing import cast

import click
import pytest

from quart import abort
from quart import Blueprint
from quart import g
from quart import Quart
from quart import render_template_string
from quart import request
from quart import ResponseReturnValue
from quart import websocket
from quart.views import MethodView


async def test_blueprint_route() -> None:
    app = Quart(__name__)
    blueprint = Blueprint("blueprint", __name__)

    @blueprint.route("/page/")
    async def route() -> ResponseReturnValue:
        return "OK"

    app.register_blueprint(blueprint)

    async with app.test_request_context("/page/"):
        assert request.blueprint == "blueprint"


async def test_blueprint_websocket() -> None:
    app = Quart(__name__)
    blueprint = Blueprint("blueprint", __name__)

    @blueprint.websocket("/ws/")
    async def ws() -> None:
        while True:
            await websocket.send(websocket.blueprint.encode())

    app.register_blueprint(blueprint)

    test_client = app.test_client()
    async with test_client.websocket("/ws/") as test_websocket:
        result = await test_websocket.receive()
    assert cast(bytes, result) == b"blueprint"


async def test_blueprint_url_prefix() -> None:
    app = Quart(__name__)
    blueprint = Blueprint("blueprint", __name__)
    prefix = Blueprint("prefix", __name__, url_prefix="/prefix")

    @app.route("/page/")
    @blueprint.route("/page/")
    @prefix.route("/page/")
    async def route() -> ResponseReturnValue:
        return "OK"

    app.register_blueprint(blueprint, url_prefix="/blueprint")
    app.register_blueprint(prefix)

    async with app.test_request_context("/page/"):
        assert request.blueprint is None

    async with app.test_request_context("/prefix/page/"):
        assert request.blueprint == "prefix"

    async with app.test_request_context("/blueprint/page/"):
        assert request.blueprint == "blueprint"


async def test_empty_path_with_url_prefix() -> None:
    app = Quart(__name__)
    prefix = Blueprint("prefix", __name__, url_prefix="/prefix")

    @prefix.route("")
    async def empty_path_route() -> ResponseReturnValue:
        return "OK"

    app.register_blueprint(prefix)

    test_client = app.test_client()
    response = await test_client.get("/prefix")
    assert response.status_code == 200
    assert await response.get_data() == b"OK"


async def test_blueprint_template_filter() -> None:
    app = Quart(__name__)
    blueprint = Blueprint("blueprint", __name__)

    @blueprint.app_template_filter()
    def reverse(value: str) -> str:
        return value[::-1]

    @blueprint.route("/")
    async def route() -> ResponseReturnValue:
        return await render_template_string("{{ name|reverse }}", name="hello")

    app.register_blueprint(blueprint)

    response = await app.test_client().get("/")
    assert b"olleh" in (await response.get_data())


async def test_blueprint_error_handler() -> None:
    app = Quart(__name__)
    blueprint = Blueprint("blueprint", __name__)

    @blueprint.route("/error/")
    async def error() -> ResponseReturnValue:
        abort(409)
        return "OK"

    @blueprint.errorhandler(409)
    async def handler(_: Exception) -> ResponseReturnValue:
        return "Something Unique", 409

    app.register_blueprint(blueprint)

    response = await app.test_client().get("/error/")
    assert response.status_code == 409
    assert b"Something Unique" in (await response.get_data())


async def test_blueprint_method_view() -> None:
    app = Quart(__name__)
    blueprint = Blueprint("blueprint", __name__)

    class Views(MethodView):
        async def get(self) -> ResponseReturnValue:
            return "GET"

        async def post(self) -> ResponseReturnValue:
            return "POST"

    blueprint.add_url_rule("/", view_func=Views.as_view("simple"))

    app.register_blueprint(blueprint)

    test_client = app.test_client()
    response = await test_client.get("/")
    assert "GET" == (await response.get_data(as_text=True))
    response = await test_client.post("/")
    assert "POST" == (await response.get_data(as_text=True))


@pytest.mark.parametrize(
    "cli_group, args",
    [
        ("named", ["named", "cmd"]),
        (None, ["cmd"]),
        (Ellipsis, ["blueprint", "cmd"]),
    ],
)
def test_cli_blueprints(cli_group: str | None, args: list[str]) -> None:
    app = Quart(__name__)

    blueprint = Blueprint("blueprint", __name__, cli_group=cli_group)

    @blueprint.cli.command("cmd")
    def command() -> None:
        click.echo("command")

    app.register_blueprint(blueprint)

    app_runner = app.test_cli_runner()
    result = app_runner.invoke(args=args)

    assert "command" in result.output


@pytest.mark.parametrize(
    "parent_init, child_init, parent_registration, child_registration",
    [
        ("/parent", "/child", None, None),
        ("/parent", None, None, "/child"),
        (None, None, "/parent", "/child"),
        ("/other", "/something", "/parent", "/child"),
    ],
)
async def test_nesting_url_prefixes(
    parent_init: str | None,
    child_init: str | None,
    parent_registration: str | None,
    child_registration: str | None,
) -> None:
    app = Quart(__name__)

    parent = Blueprint("parent", __name__, url_prefix=parent_init)
    child = Blueprint("child", __name__, url_prefix=child_init)

    @child.route("/")
    def index() -> ResponseReturnValue:
        return "index"

    parent.register_blueprint(child, url_prefix=child_registration)
    app.register_blueprint(parent, url_prefix=parent_registration)

    test_client = app.test_client()
    response = await test_client.get("/parent/child/")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "parent_subdomain, child_subdomain, expected_subdomain",
    [
        (None, None, None),
        ("parent", None, "parent"),
        (None, "child", "child"),
        ("parent", "child", "child.parent"),
    ],
)
async def test_nesting_subdomains(
    parent_subdomain: str | None,
    child_subdomain: str | None,
    expected_subdomain: str | None,
) -> None:
    app = Quart(__name__)
    domain_name = "domain.tld"
    app.config["SERVER_NAME"] = domain_name

    parent = Blueprint("parent", __name__, subdomain=parent_subdomain)
    child = Blueprint("child", __name__, subdomain=child_subdomain)

    @child.route("/")
    def index() -> ResponseReturnValue:
        return "index"

    parent.register_blueprint(child)
    app.register_blueprint(parent)

    test_client = app.test_client()
    response = await test_client.get("/", subdomain=expected_subdomain)
    assert response.status_code == 200


async def test_nesting_and_sibling() -> None:
    app = Quart(__name__)

    parent = Blueprint("parent", __name__, url_prefix="/parent")
    child = Blueprint("child", __name__, url_prefix="/child")

    @child.route("/")
    def index() -> ResponseReturnValue:
        return "index"

    parent.register_blueprint(child)
    app.register_blueprint(parent)
    app.register_blueprint(child, url_prefix="/sibling")

    test_client = app.test_client()
    response = await test_client.get("/parent/child/")
    assert response.status_code == 200
    response = await test_client.get("/sibling/")
    assert response.status_code == 200


def test_unique_blueprint_names() -> None:
    app = Quart(__name__)
    bp = Blueprint("bp", __name__)
    bp2 = Blueprint("bp", __name__)

    app.register_blueprint(bp)

    with pytest.raises(ValueError):
        app.register_blueprint(bp)

    with pytest.raises(ValueError):
        app.register_blueprint(bp2, url_prefix="/a")

    app.register_blueprint(bp, name="alt")


async def test_nested_blueprint() -> None:
    app = Quart(__name__)

    parent = Blueprint("parent", __name__, url_prefix="/parent")
    child = Blueprint("child", __name__)
    grandchild = Blueprint("grandchild", __name__)
    sibling = Blueprint("sibling", __name__)

    @parent.errorhandler(403)
    async def forbidden(_: Exception) -> ResponseReturnValue:
        return "Parent no", 403

    @parent.route("/")
    async def parent_index() -> ResponseReturnValue:
        return "Parent yes"

    @parent.route("/no")
    async def parent_no() -> ResponseReturnValue:
        abort(403)

    @child.route("/")
    async def child_index() -> ResponseReturnValue:
        return "Child yes"

    @child.route("/no")
    async def child_no() -> ResponseReturnValue:
        abort(403)

    @grandchild.errorhandler(403)
    async def grandchild_forbidden(_: Exception) -> ResponseReturnValue:
        return "Grandchild no", 403

    @grandchild.route("/")
    async def grandchild_index() -> ResponseReturnValue:
        return "Grandchild yes"

    @grandchild.route("/no")
    async def grandchild_no() -> ResponseReturnValue:
        abort(403)

    @sibling.route("/sibling")
    async def sibling_index() -> ResponseReturnValue:
        return "Sibling yes"

    child.register_blueprint(grandchild, url_prefix="/grandchild")
    parent.register_blueprint(child, url_prefix="/child")
    parent.register_blueprint(sibling)
    app.register_blueprint(parent)
    app.register_blueprint(parent, url_prefix="/alt", name="alt")

    client = app.test_client()

    assert (await (await client.get("/parent/")).get_data()) == b"Parent yes"
    assert (await (await client.get("/parent/child/")).get_data()) == b"Child yes"
    assert (await (await client.get("/parent/sibling")).get_data()) == b"Sibling yes"
    assert (await (await client.get("/alt/sibling")).get_data()) == b"Sibling yes"
    assert (
        await (await client.get("/parent/child/grandchild/")).get_data()
    ) == b"Grandchild yes"
    assert (await (await client.get("/parent/no")).get_data()) == b"Parent no"
    assert (await (await client.get("/parent/child/no")).get_data()) == b"Parent no"
    assert (
        await (await client.get("/parent/child/grandchild/no")).get_data()
    ) == b"Grandchild no"


async def test_blueprint_renaming() -> None:
    app = Quart(__name__)

    bp = Blueprint("bp", __name__)
    bp2 = Blueprint("bp2", __name__)

    @bp.get("/")
    async def index() -> str:
        return request.endpoint

    @bp.get("/error")
    async def error() -> str:
        abort(403)

    @bp.errorhandler(403)
    async def forbidden(_: Exception) -> ResponseReturnValue:
        return "Error", 403

    @bp2.get("/")
    async def index2() -> str:
        return request.endpoint

    bp.register_blueprint(bp2, url_prefix="/a", name="sub")
    app.register_blueprint(bp, url_prefix="/a")
    app.register_blueprint(bp, url_prefix="/b", name="alt")

    client = app.test_client()

    assert (await (await client.get("/a/")).get_data()) == b"bp.index"
    assert (await (await client.get("/b/")).get_data()) == b"alt.index"
    assert (await (await client.get("/a/a/")).get_data()) == b"bp.sub.index2"
    assert (await (await client.get("/b/a/")).get_data()) == b"alt.sub.index2"
    assert (await (await client.get("/a/error")).get_data()) == b"Error"
    assert (await (await client.get("/b/error")).get_data()) == b"Error"


def test_self_registration() -> None:
    bp = Blueprint("bp", __name__)

    with pytest.raises(ValueError):
        bp.register_blueprint(bp)


async def test_nested_callback_order() -> None:
    app = Quart(__name__)

    parent = Blueprint("parent", __name__)
    child = Blueprint("child", __name__)

    @app.before_request
    async def app_before1() -> None:
        g.setdefault("seen", []).append("app_1")

    @app.teardown_request
    async def app_teardown1(exc: BaseException | None = None) -> None:
        assert g.seen.pop() == "app_1"

    @app.before_request
    async def app_before2() -> None:
        g.setdefault("seen", []).append("app_2")

    @app.teardown_request
    async def app_teardown2(exc: BaseException | None = None) -> None:
        assert g.seen.pop() == "app_2"

    @app.context_processor
    async def app_ctx() -> dict:
        return dict(key="app")

    @parent.before_request
    async def parent_before1() -> None:
        g.setdefault("seen", []).append("parent_1")

    @parent.teardown_request
    async def parent_teardown1(exc: BaseException | None = None) -> None:
        assert g.seen.pop() == "parent_1"

    @parent.before_request
    async def parent_before2() -> None:
        g.setdefault("seen", []).append("parent_2")

    @parent.teardown_request
    async def parent_teardown2(exc: BaseException | None = None) -> None:
        assert g.seen.pop() == "parent_2"

    @parent.context_processor
    async def parent_ctx() -> dict:
        return dict(key="parent")

    @child.before_request
    async def child_before1() -> None:
        g.setdefault("seen", []).append("child_1")

    @child.teardown_request
    async def child_teardown1(exc: BaseException | None = None) -> None:
        assert g.seen.pop() == "child_1"

    @child.before_request
    async def child_before2() -> None:
        g.setdefault("seen", []).append("child_2")

    @child.teardown_request
    async def child_teardown2(exc: BaseException | None = None) -> None:
        assert g.seen.pop() == "child_2"

    @child.context_processor
    async def child_ctx() -> dict:
        return dict(key="child")

    @child.route("/a")
    async def a() -> str:
        return ", ".join(g.seen)

    @child.route("/b")
    async def b() -> str:
        return await render_template_string("{{ key }}")

    parent.register_blueprint(child)
    app.register_blueprint(parent)

    client = app.test_client()
    assert (
        await (await client.get("/a")).get_data()
    ) == b"app_1, app_2, parent_1, parent_2, child_1, child_2"
    assert (await (await client.get("/b")).get_data()) == b"child"
