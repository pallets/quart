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

Advanced usage
--------------

You may wish to completely control how the request body is consumed,
most likely to consume the data as it is received. To do this quart
provides methods to iterate over the body,

.. code-block:: python

    from async_timeout import timeout

    @app.route('/', methods=['POST'])
    async def index():
        async with timeout(app.config['BODY_TIMEOUT']):
            async for data in request.body:
                ...

.. note::

   The above snippet uses `Async-Timeout
   <https://github.com/aio-libs/async-timeout>`_ to ensure the body is
   received within the timeout specified.

.. warning::

   Whilst the other request methods and attributes for accessing the
   body will timeout if the client takes to long send the
   request. Usage of :attr:`~quart.wrappers.request.Request.body` will
   not and it is up to you to wrap usage in a timeout.

.. warning::

    Iterating over the body consumes the data, so any further usage of
    the data is not possible unless it is saved during the iteration.
