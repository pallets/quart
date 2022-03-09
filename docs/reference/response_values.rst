.. _response_values:

Response Return Values
======================

Response functions can return a number of different types as the
response value which will trigger different responses to the
client. The possible direct returns are,

Response Values
---------------

str
'''

.. code-block:: python

    return "Hello"
    return await render_template("index.html")

A solitary string return indicates that you intend to return a string
mimetype ``text/html``. The string will be encoded using the default
:attr:`~quart.wrappers._BaseRequestResponse.charset`.

dict
''''

.. code-block:: python

    return {"a": "b"}

A solitary dict return indicates that you intend to return json,
``application/json``. The jsonify function will be used to encode the
dictionary.

Response
''''''''

.. code-block:: python

    @app.route('/')
    async def route_func():
        return Response("Hello")

Returning a Response instance indicates that you know exactly what you
wish to return.

AsyncGenerator[bytes, None]
'''''''''''''''''''''''''''

.. code-block:: python

    @app.route('/')
    async def route_func():

        async def agen():
            data = await something
            yield data

        return agen()

Returning an async generator allows for the response to be streamed to
the client, thereby lowing the peak memory usage, if combined with a
``Transfer-Encoding`` header with value ``chunked``.

Generator[bytes, None, None]
''''''''''''''''''''''''''''

.. code-block:: python

    @app.route('/')
    async def route_func():

        def gen():
            yield data

        return gen()

Returning an generator allows for the response to be streamed to the
client, thereby lowing the peak memory usage, if combined with a
``Transfer-Encoding`` header with value ``chunked``.

Combinations
------------

Any of the above Response Values can be combined, as described,

Tuple[ResponseValue, int]
'''''''''''''''''''''''''

.. code-block:: python

    @app.route('/')
    async def route_func():
        return "Hello", 200

A tuple of a Response Value and a integer indicates that you intend to
specify the status code.

Tuple[str, int, Dict[str, str]]
'''''''''''''''''''''''''''''''

.. code-block:: python

    @app.route('/')
    async def route_func():
        return "Hello", 200, {'X-Header': 'Value'}

A tuple of a Response Value, integer and dictionary indicates that you intend
to specify additional headers.
