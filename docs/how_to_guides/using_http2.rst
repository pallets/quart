.. _using_http2:

Using HTTP/2
============

`HTTP/2 <https://http2.github.io/>`__ is the second major version of
the Hyper Text Transfer Protocol used to transfer web data.

.. note::

    Not all ASGI Servers support HTTP/2. The recommended ASGI server,
    Hypercorn, does.

To use HTTP/2 in development you will need to create some SSL
certificates and run Quart with SSL.

Server push or push promises
----------------------------

With `HTTP/2 <http://httpwg.org/specs/rfc7540.html#PushResources>`__
the server can choose to pre-emptively push additional responses to
the client, this is termed a server push and the response itself is
called a push promise. Server push is very useful when the server
knows the client will likely initiate a request, say for the css or js
referenced in a html response.

.. note::

   Browsers are deprecating support for server push, and usage is not
   recommended. This section is kept for reference.

In Quart server push can be initiated during a request via the
function :func:`~quart.helpers.make_push_promise`, for example,

.. code-block:: python

    async def index():
        await make_push_promise(url_for('static', filename='css/minimal.css'))
        return await render_template('index.html')

The push promise will include (copy) header values present in the
request that triggers the push promise. These are to ensure that the
push promise is responded too as if the request had made it. A good
example is the ``Accept`` header. The full set of copied headers are
``SERVER_PUSH_HEADERS_TO_COPY`` in the request module.

.. note::

    This functionality is only useable with ASGI servers that
    implement the ``HTTP/2 Server Push`` extension. If the server does
    not support this extension Quart will ignore the push promises (as
    with HTTP/1 connections). Hypercorn, the recommended ASGI server,
    supports this extension.

When testing server push,the :class:`~quart.testing.QuartClient`
``push_promises`` list will contain every push promise as a tuple of
the path and headers, for example,

.. code-block:: python

    async def test_push_promise():
        test_client = app.test_client()
        await test_client.get("/push")
        assert test_client.push_promises[0] == ("/", {})

HTTP/2 clients
--------------

At the time of writing there aren't that many HTTP/2 clients. The best
option is to use a browser and inspect the network connections (turn
on the protocol information). Otherwise curl can be used, if HTTP/2
support is `installed <https://curl.haxx.se/docs/http2.html>`_, as so,

.. code-block:: console

    $ curl --http2 ...

If you wish to communicate via HTTP/2 in python `httpx
<https://github.com/encode/httpx>`_ is the best choice.
