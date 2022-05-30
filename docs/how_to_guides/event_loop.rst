.. _event_loop:

Customise the Event Loop
========================

Customising the event loop is often desired in order to use Quart with
another library whilst ensuring both use the same loop.  The best practice is
to create/initialise the third party within the loop created by Quart,
by using :ref:`startup_shutdown` ``before_serving`` functions as so,

.. code-block:: python

    @app.before_serving
    async def startup():
        loop = asyncio.get_event_loop()
        app.smtp_server = loop.create_server(aiosmtpd.smtp.SMTP, port=1025)
        loop.create_task(app.smtp_server)

    @app.after_serving
    async def shutdown():
        app.smtp_server.close()

Do not follow this pattern, typically seen in examples, because this creates a
new loop separate from the Quart loop for ThirdParty,

.. code-block:: python

    loop = asyncio.get_event_loop()
    third_party = ThirdParty(loop)
    app.run()  # A new loop is created by default

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

or to use the ``app.run_task`` method,

.. code-block:: python

    loop = asyncio.get_event_loop()
    third_party = ThirdParty(loop)
    loop.run_until_complete(app.run_task())

the Hypercorn (production) solution is to utilise the `Hypercorn API
<https://pgjones.gitlab.io/hypercorn/how_to_guides/api_usage.html#api-usage>`_ to do the
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
