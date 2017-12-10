.. _request_body:

Consuming the request body
==========================

Requests can come with a body, for example for a POST request the body
can include form encoded data from a webpage or JSON encoded data from
a client. The body is sent after the request line and headers for both
HTTP/1 and HTTP/2. This allows Quart to trigger the app's request
handling code before the full body has been received. Additionally the
requester can choose to stream the request body, especially if the
body is large as is often the case when sending files.

Quart follows Flask and provides methods to await the entire body
before continuing,

.. code-block:: python

    @app.route('/', methods=['POST'])
    async def index():
        await request.get_data()

alternatively, for advanced usage, quart provides methods to iterate
over the body as it is received,

.. code-block:: python

    @app.route('/', methods=['POST'])
    async def index():
        async for data in request.body:
            ...

.. warning::

    Iterating over the body consumes the data, so any further usage of
    the data is not possible unless it is saved during the iteration.
