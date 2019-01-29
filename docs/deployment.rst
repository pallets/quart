.. _deployment:

Deploying Quart
===============

It is not recommended to run Quart directly (via
:meth:`~quart.app.Quart.run`) in production. Instead it is recommended
that Quart be run using `Hypercorn
<https://gitlab.com/pgjones/hypercorn>`_ or an alternative ASGI
server. Hypercorn is installed with Quart and is used to serve
requests by default (e.g. with :meth:`~quart.app.Quart.run`).

To use Quart with an ASGI server simply point the server at the Quart
application, for example for a simple application in a file called
``example.py``,

.. code-block:: python

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def hello():
        return 'Hello World'

you can run with Hypercorn using,

.. code-block:: bash

    hypercorn example:app

See the `Hypercorn docs <https://pgjones.gitlab.io/hypercorn/>`_.

Alternative ASGI Servers
------------------------

==================================================== ====== =========== ==================
Server name                                          HTTP/2 Server Push Websocket Response
==================================================== ====== =========== ==================
`Hypercorn <https://gitlab.com/pgjones/hypercorn>`_  ✓      ✓           ✓
`Uvicorn <https://github.com/encode/uvicorn>`_       ✗      ✗           ✗
`Daphne <https://https://github.com/django/daphne>`_ ✓      ✗           ✗
==================================================== ====== =========== ==================

HTTP/2 deployment
-----------------

Most web browsers only support HTTP/2 over a TLS connection with
TLSv1.2 or better and certain ciphers. So to use these features with
Quart you must chose an ASGI server that implements HTTP/2 and use
SSL.

Serverless deployment
---------------------

To deploy Quart in a FaaS setting you will need to use a specialised
ASGI function adapter. `Mangum <https://github.com/erm/mangum>`_ is
recommended for this and can be as simple as,

.. code-block:: python

    from mangum.platforms.aws.adapter import AWSLambdaAdapter
    # from mangum.platforms.azure.adapter import AzureFunctionAdapter
    from quart import Quart

    app = Quart(__name__)

    @app.route("/")
    async def index():
        return "Hello, world!"

    handler = AWSLambdaAdapter(app)  # optionally set debug=True
    # handler = AzureFunctionAdapter(app)
