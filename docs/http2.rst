.. _http2:

Using HTTP/2
============

Serving HTTP/2
--------------

To serve HTTP/2 in production see `deployment`_, for development you
will need to create an SSL context and run the app with that
context. For example the following can be used,

.. code-block:: python

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
    ssl_context.set_ciphers('ECDHE+AESGCM')
    ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
    app.run(port=5000, ssl=ssl_context)

note that it sets the ciphers, valid versions and ALPN protocols
required for HTTP/2, http/1.1 can be removed to support only HTTP/2.

Server push or push promises
----------------------------

With HTTP/2 the server can choose to push additional responses to the
client, this is termed a server push and the initial response itself
is called a push promise. This is very useful when the server knows
the client will likely initiate a request, say for the css or js
referenced in a html response.

In Quart server push can be initiated by adding the paths to push
to any response, for example,

.. code-block:: python

    async def index():
        result = await render_template('index.html')
        response = await make_response(result)
        response.push_promises.add(url_for('static', filename='css/base.css'))
        return response

see also :attr:`~quart.wrappers.Response.push_promises`.
