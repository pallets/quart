.. _websockets:

Using websockets
================

To use a websocket declare a websocket function rather than a route
function, like so,

.. code-block:: python

    @app.websocket('/ws')
    async def ws():
        while True:
            data = await websocket.receive()
            await websocket.send(data)

``websocket`` is a global like ``request`` and shares many of the same
attribtues such as ``headers``.

Manually rejecting or accepting websockets
------------------------------------------

A websocket connection is created by accepting a HTTP upgrade request,
however a server can choose to reject a websocket request. To do so
just return from the websocket function as you would with a route function,

.. code-block:: python

    @app.websocket('/ws')
    async def ws():
        if (
            websocket.authorization.username != USERNAME or
            websocket.authorization.password != PASSWORD
        ):
            return 'Invalid password', 403  # or abort(403)
        else:
            websocket.accept()  # Automatically invoked by receive or send
            ...

Sending and receiving independently
-----------------------------------

The first example given requires the client to send a message for the
server to respond. To send and receive independently requires
independent tasks,

.. code-block:: python

    async def sending():
        while True:
            await websocket.send(...)

    async def receiving():
        while True:
            data = await websocket.receive()
            ...

    @app.websocket('/ws')
    async def ws():
        producer = asyncio.create_task(sending())
        consumer = asyncio.create_task(receiving())
        await asyncio.gather(producer, consumer)

The gather line is critical, as without it the websocket function
would return triggering Quart to send a HTTP response.

Testing websockets
------------------

To test a websocket route use the test_client like so,

.. code-block:: python

    test_client = app.test_client()
    with test_client.websocket('/ws/') as test_websocket:
        await test_websocket.send(data)
        result = await test_websocket.receive()

If the websocket route returns a response the test_client will raise a
:class:`~quart.testing.WebsocketResponse` exception with a
:attr:`~quart.testing.WebsocketResponse.response` attribute. For
example,

.. code-block:: python

    test_client = app.test_client()
    with test_client.websocket('/ws/') as test_websocket:
        try:
            await test_websocket.send(data)
        except WebsocketResponse as error:
            assert error.response.status_code == 401
