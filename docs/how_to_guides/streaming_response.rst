.. _streaming_response:

Streaming response
==================

Quart supports responses that are meant to be streamed to the client,
rather than received in one block. If you are interested in streaming
the request data see :ref:`request_body` or for duplex streaming see
:ref:`websockets`.

To stream a response the view-function should return an asynchronous
generator that yields bytes. This generator can be returned with a
status code and headers as normal. For example to stream the time
every second,

.. code-block:: python

    @app.route('/')
    async def stream_time():
        async def async_generator():
            time = datetime.isoformat()
            yield time.encode()
        return async_generator(), 200, {'X-Something': 'value'}

With context
''''''''''''

If you want to make use of the ``request`` context whilst streaming
you will need to use the :func:`quart.helpers.stream_with_context`
decorator,

.. code-block:: python

    @app.route('/')
    async def stream_time():
        @stream_with_context
        async def async_generator():
            time = datetime.isoformat()
            yield time.encode()
        return async_generator(), 200, {'X-Something': 'value'}

Timeout
'''''''

Quart by default will timeout long responses to protect against
possible denial of service attacks, see :ref:`dos_mitigations`. This
may be undesired for streaming responses, e.g. an indefinite
stream. The timeout can be disabled globally, however this could make
other routes DOS vulnerable, therefore the recommendation is to set
the timeout attribute on a specific response to ``None``,

.. code-block:: python

    from quart import make_response

    @app.route('/sse')
    async def stream_time():
        ...
        response = await make_response(async_generator())
        response.timeout = None  # No timeout for this route
        return response

Server Sent Events
''''''''''''''''''

See the :ref:`broadcast_tutorial` for details on how to utilise server
sent events.

Testing
'''''''

The test client :meth:`~quart.testing.client.QuartClient.get` and
associated methods will collate the entire streamed response. If you
want to test that the route actually streams the response, or to test
routes that stream until the client disconnects you will need to use
the :meth:`~quart.testing.client.QuartClient.request` method,

.. code-block:: python

    async def test_stream() -> None:
        test_client = app.test_client()
        async with test_client.request(..) as connection:
            data = await connection.receive()
            assert data ...
            assert connection.status_code == 200
            ...
            await connection.disconnect()  # For infinite streams
