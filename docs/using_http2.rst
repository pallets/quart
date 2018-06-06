.. _using_http2:

Using HTTP/2
============

`HTTP/2 <https://http2.github.io/>`_ is the second major version of
the Hyper Text Transfer Protocol used to transfer web data.

.. note::

    Not all ASGI Servers support HTTP/2. The recommended ASGI server,
    Hypercorn, does.

To use HTTP/2 in development you will need to create some SSL
certificates and run Quart with SSL. See the :ref:`http2_tutorial`.

Server push or push promises
----------------------------

With `HTTP/2 <http://httpwg.org/specs/rfc7540.html#PushResources>`_
the server can choose to pre-emptively push additional responses to
the client, this is termed a server push and the response itself is
called a push promise. Server push is very useful when the server
knows the client will likely initiate a request, say for the css or js
referenced in a html response.

In Quart server push can be initiated by adding the paths to push to
any response, for example,

.. code-block:: python

    async def index():
        result = await render_template('index.html')
        response = await make_response(result)
        response.push_promises.add(url_for('static', filename='css/base.css'))
        return response

see also :attr:`~quart.wrappers.Response.push_promises`.

.. note::

    This functionality is only useable with ASGI servers that
    implement the ``HTTP/2 Server Push`` extension. If the server does
    not support this extension Quart will ignore the push promises (as
    with HTTP/1 connections). Hypercorn, the recommended ASGI server,
    supports this extension.

HTTP/2 clients
''''''''''''''

At the time of writing there aren't that many HTTP/2 clients. The best
option is to use a browser and inspect the network connections (turn
on the protocol information). Otherwise curl can be used, if HTTP/2
support is `installed <https://curl.haxx.se/docs/http2.html>`_, as so,

.. code-block:: console

    $ curl --http2 ...

If you wish to communicate via HTTP/2 in python the `Hyper
<https://hyper.readthedocs.io>`_ library is the best choice. It can be
configured to work with requests.
