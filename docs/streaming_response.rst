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

Server Sent Events
''''''''''''''''''

See the :ref:`broadcast_tutorial` for details on how to utilise server
sent events.
