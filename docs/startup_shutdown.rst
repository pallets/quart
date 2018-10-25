.. _startup_shutdown:

Startup and Shutdown
===================

A provisional addition to the ASGI specification adds the ability for
coroutines to be awaited before a byte is received, ``startup`` and
after the final byte is sent ``shutdown``. This is particularly useful
for creating and destroying connection pools. Quart provisionally
supports this via :func:`~quart.app.Quart.before_serving` and
:func:`~quart.app.Quart.after_serving` decorators which in the same
way as :func:`~quart.app.Quart.before_first_request`.

The decorated functions are called within the app context, allowing
``current_app`` and ``g`` to be used.

To use this functionality simply do the following,

.. code-block:: python

    @app.before_serving
    async def create_db_pool():
        g.db_pool = await ...

    @app.after_serving
    async def create_db_pool():
        await g.db_pool.close()
