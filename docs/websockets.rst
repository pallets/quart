.. _websockets:

Using websockets
================

To use a websocket declare a websocket function rather than a route
function, like so,

.. code-block:: python

    @app.websocket('/ws')
    async def ws():
        while True:
            await websocket.receive()

``websocket`` is a global.

Testing websockets
------------------

To test a websocket route use the test_client like so,

.. code-block:: python

    test_client = app.test_client()
    with test_client.websocket('/ws/') as test_websocket:
        await test_websocket.send(data)
        result = await test_websocket.receive()
