.. _http2:

Serving HTTP/2
==============

`HTTP/2 <https://http2.github.io/>`_ is the second major version of
the Hyper Text Transfer Protocol used to transfer web data. Quart
directly supports HTTP/2, see :ref:`http2_discussion`.

HTTP/2 has been designed with security in mind with most clients
(notably web browsers) only supporting HTTP/2 over HTTPS, see
:ref:`http_discussion` for more details. You will need then to create
or acquire certificates, see :ref:`ssl` to learn how to.

To serve HTTP/2 you will need to configure SSL, in production please
see :ref:`deployment` for the best practice. For development you will
should create an SSL context and run the app with that context. In
both cases it is necessary to set the minimal cipher set to (at least)
``ECDHE+AESGM`` and the minimal TLS version to 1.2. To do so the
following can be used,

.. code-block:: python

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
    ssl_context.set_ciphers('ECDHE+AESGCM')
    ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
    app.run(port=5000, ssl=ssl_context)

which assumes your SSL certificates are ``cert.pem`` and ``key.pem``.
Note that you must specify the ALPN protocols as ``h2`` and
``http/1.1`` in order to serve both, or you can remove one or the
other if desired.

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
