.. _startup_shutdown:

Startup and Shutdown
====================

A provisional addition to the ASGI specification adds the ability for
coroutines to be awaited before a byte is received, ``startup`` and
after the final byte is sent ``shutdown``. This is particularly useful
for creating and destroying connection pools. Quart provisionally
supports this via :func:`~quart.app.Quart.before_serving` and
:func:`~quart.app.Quart.after_serving` decorators which in the same
way as :func:`~quart.app.Quart.before_first_request`.

The decorated functions are all called within the app context,
allowing ``current_app`` and ``g`` to be used.

.. note::

    ``g`` should be used with caution as it will be reset after all
    the ``before_serving`` functions have completed (it can be used
    between functions). If you want to create something that is used
    in routes try storing on the app instead.

To use this functionality simply do the following,

.. code-block:: python

    @app.before_serving
    async def create_db_pool():
        app.db_pool = await ...
        g.something = something

    @app.before_serving
    async def use_g():
        g.something.do_something()

    @app.route("/")
    async def index():
        app.db_pool.execute(...)
        # g.something will not be available here

    @app.after_serving
    async def create_db_pool():
        await app.db_pool.close()
