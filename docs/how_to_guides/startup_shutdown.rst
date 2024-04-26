.. _startup_shutdown:

Startup and Shutdown
====================

The `ASGI lifespan specification`_ includes the ability for awaiting
coroutines before the first byte is received and after the final byte
is sent, through the ``startup`` and ``shutdown`` lifespan events.
This is particularly useful for creating and destroying connection
pools.  Quart supports this via the decorators
:func:`~quart.app.Quart.before_serving`,
:func:`~quart.app.Quart.after_serving`, and
:func:`~quart.app.Quart.while_serving` which expects a function that
returns a generator.

.. _ASGI lifespan specification: https://github.com/django/asgiref/blob/master/specs/lifespan.rst

The decorated functions are all called within the app context,
allowing ``current_app`` and ``g`` to be used.

.. warning::

    Use ``g`` with caution, as it will reset after startup, i.e. after
    all the ``before_serving`` functions complete and after the
    initial yield in a while serving generator. It can still be used
    within this context. If you want to create something used in
    routes, try storing it on the app instead.

To use this functionality simply do the following:

.. code-block:: python

    @app.before_serving
    async def create_db_pool():
        app.db_pool = await ...
        g.something = something

    @app.before_serving
    async def use_g():
        g.something.do_something()

    @app.while_serving
    async def lifespan():
        ...  # startup
        yield
        ...  # shutdown

    @app.route("/")
    async def index():
        app.db_pool.execute(...)
        # g.something is not available here

    @app.after_serving
    async def create_db_pool():
        await app.db_pool.close()

Testing
-------

Quart's test client works on a request lifespan and hence does not
call ``before_serving``, or ``after_serving`` functions, nor advance
the ``while_serving`` generator. Instead Quart's test app can be used,
for example

.. code-block:: python

    @pytest_asyncio.fixture(name="app", scope="function")
    async def _app():
        app = create_app()  # Initialize app
        async with app.test_app() as test_app:
            yield test_app

The app fixture can then be used as normal, knowing that the
``before_serving``, and ``after_serving`` functions have been called,
and the ``while_serving`` generator has been advanced,

.. code-block:: python

    async def test_index(app):
        test_client = app.test_client()
        await test_client.get("/")
        ...
