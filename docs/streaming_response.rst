.. _streaming_response:

Streaming response
==================

Quart supports responses that are meant to be streamed to the client,
rather than received in one block. If you are interested in streaming
the request data see :ref:`request_body` or in two way streaming see
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

Timeout
'''''''

Quart by default will timeout long responses to protect against
possible denial of service attacks, see :ref:`dos_mitigations`. This
may be undesired for streaming responses, e.g. an indefinite
stream. The timeout can be disabled gloablly, however this could make
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
