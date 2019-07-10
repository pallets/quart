.. _event_loop:

Customise the Event Loop
========================

Customising the event loop is often desired in order to use Quart with
another library whilst ensuring both use the same loop. A typical
example is,

.. code-block:: python

    loop = asyncio.get_event_loop()
    third_party = ThirdParty(loop)
    app.run()  # A new loop is created by default

which as written will fail as Quart will create and use a different
event loop to the third party. In this situation the best practice is
to create/initialise the third party within the loop created by Quart,
by using a :ref:`startup_shutdown` ``before_serving`` function as so,

.. code-block:: python

    @app.before_serving
    async def startup():
        loop = asyncio.get_event_loop()
        third_party = ThirdParty(loop)

Controlling the event loop
--------------------------

It is the ASGI server running running Quart that owns the event loop
that Quart runs within, by default the server is Hypercorn. Both Quart
and Hypercorn allow the loop to be specified, the Quart shortcut in
development is to pass the loop to the ``app.run`` method,

.. code-block:: python

    loop = asyncio.get_event_loop()
    third_party = ThirdParty(loop)
    app.run(loop=loop)

the Hypercorn solution is to utilise the `Hypercorn API
<https://pgjones.gitlab.io/hypercorn/api_usage.html>`_ to do the
following,

.. code-block:: python

    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    ...
    loop = asyncio.get_event_loop()
    third_party = ThirdParty(loop)
    loop.run_until_complete(serve(app, Config()))
    # or even
    await serve(app, config)
