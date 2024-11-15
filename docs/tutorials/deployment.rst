.. _deployment:

Deploying Quart
===============

It is not recommended to run Quart directly (via
:meth:`~quart.app.Quart.run`) in production. Instead it is recommended
that Quart be run using `Hypercorn
<https://github.com/pgjones/hypercorn>`_ or an alternative ASGI
server. This is because the :meth:`~quart.app.Quart.run` enables
features that help development yet slow production
performance. Hypercorn is installed with Quart and will be used to
serve requests in development mode by default (e.g. with
:meth:`~quart.app.Quart.run`).

To use Quart with an ASGI server simply point the server at the Quart
application, for example,

.. code-block:: python
   :caption: example.py

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def hello():
        return 'Hello World'

you can run with Hypercorn using,

.. code-block:: bash

    hypercorn example:app

See the `Hypercorn docs <https://hypercorn.readthedocs.io/>`_.

Alternative ASGI Servers
------------------------

Alongside `Hypercorn <https://github.com/pgjones/hypercorn>`_, `Daphne
<https://github.com/django/daphne>`_, and `Uvicorn
<https://github.com/encode/uvicorn>`_ are available ASGI servers that
work with Quart.

Serverless deployment
---------------------

To deploy Quart in an AWS Lambda & API Gateway setting you will need to use a specialised
ASGI function adapter. `Mangum <https://github.com/erm/mangum>`_ is
recommended for this and can be as simple as,

.. code-block:: python

    from mangum import Mangum
    from quart import Quart

    app = Quart(__name__)

    @app.route("/")
    async def index():
        return "Hello, world!"

    handler = Mangum(app)  # optionally set debug=True
