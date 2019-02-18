import asyncio

import pytest

from quart import Blueprint, g, Quart, render_template_string, session


@pytest.fixture(scope='function')
def app() -> Quart:
    app = Quart(__name__)
    app.secret_key = 'secret'

    return app


@pytest.fixture(scope='function')
def blueprint() -> Blueprint:
    blueprint = Blueprint('blueprint', __name__)

    @blueprint.route('/')
    def index() -> str:
        return ''

    return blueprint


@pytest.mark.asyncio
async def test_template_render(app: Quart) -> None:
    async with app.app_context():
        rendered = await render_template_string("{{ foo }}", foo='bar')
    assert rendered == 'bar'


@pytest.mark.asyncio
async def test_default_template_context(app: Quart) -> None:
    async with app.app_context():
        g.foo = 'bar'  # type: ignore
        rendered = await render_template_string("{{ g.foo }}")
    assert rendered == 'bar'
    async with app.test_request_context('/'):
        session['foo'] = 'bar'
        rendered = await render_template_string(
            "{{ request.method }} {{ request.path }} {{ session.foo }}",
        )
    assert rendered == 'GET / bar'


@pytest.mark.asyncio
async def test_template_context_processors(app: Quart, blueprint: Blueprint) -> None:

    @blueprint.context_processor
    async def blueprint_context() -> dict:
        await asyncio.sleep(0.01)  # Test the ability to await
        return {'context': 'foo'}

    @blueprint.app_context_processor
    def app_blueprint_context() -> dict:
        return {'global_context': 'boo'}

    @app.context_processor
    def app_context() -> dict:
        return {'context': 'bar'}

    app.register_blueprint(blueprint)

    async with app.app_context():
        rendered = await render_template_string("{{ context }}")
    assert rendered == 'bar'

    async with app.test_request_context('/'):
        rendered = await render_template_string("{{ context }} {{ global_context }}")
    assert rendered == 'foo boo'

    async with app.test_request_context('/other'):
        rendered = await render_template_string("{{ context }} {{ global_context }}")
    assert rendered == 'bar boo'


@pytest.mark.asyncio
async def test_template_globals(app: Quart, blueprint: Blueprint) -> None:

    @blueprint.app_template_global()
    def blueprint_global(value: str) -> str:
        return value.upper()

    @app.template_global()
    def app_global(value: str) -> str:
        return value.lower()

    app.register_blueprint(blueprint)

    async with app.app_context():
        rendered = await render_template_string(
            "{{ app_global('BAR') }} {{ blueprint_global('foo') }}",
        )
    assert rendered == 'bar FOO'


@pytest.mark.asyncio
async def test_template_filters(app: Quart, blueprint: Blueprint) -> None:

    @blueprint.app_template_filter()
    def blueprint_filter(value: str) -> str:
        return value.upper()

    @app.template_filter()
    def app_filter(value: str) -> str:
        return value.lower()

    app.register_blueprint(blueprint)

    async with app.app_context():
        rendered = await render_template_string("{{ 'App' | app_filter }}")
    assert rendered == 'app'

    async with app.test_request_context('/'):
        rendered = await render_template_string("{{ 'App' | blueprint_filter }}")
    assert rendered == 'APP'


@pytest.mark.asyncio
async def test_template_tests(app: Quart, blueprint: Blueprint) -> None:

    @blueprint.app_template_test()
    def blueprint_test(value: int) -> bool:
        return value == 5

    @app.template_test()
    def app_test(value: int) -> bool:
        return value == 3

    app.register_blueprint(blueprint)

    async with app.app_context():
        rendered = await render_template_string("{% if 3 is app_test %}foo{% endif %}")
    assert rendered == 'foo'

    async with app.test_request_context('/'):
        rendered = await render_template_string("{% if 5 is blueprint_test %}bar{% endif %}")
    assert rendered == 'bar'
