.. _detecting_disconnection:

Detecting disconnection
=======================

If in your route or websocket handler (or code called from within it)
you are awaiting and the client disconnects the await will raise a
``CancelledError``. This can be used to detect when a client
disconnects, to allow for cleanup, for example the sse handler from
the :ref:`broadcast_tutorial` uses this to remove clients on
disconnect,

.. code-block:: python

    @app.route('/sse')
    async def sse():
        queue = asyncio.Queue()
        app.clients.add(queue)
        async def send_events():
            while True:
                try:
                    data = await queue.get()
                    event = ServerSentEvent(data)
                    yield event.encode()
                except asyncio.CancelledError:
                    app.clients.remove(queue)

or with only the relevant parts,

.. code-block:: python

    @app.route('/sse')
    async def sse():
        try:
            await ...
        except asyncio.CancelledError:
            # Has disconnected

The same applies for WebSockets, streaming the request, etc...
