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

Gunicorn deployment
-------------------

.. note::

    The Gunicorn workers are deprecated in 0.6.0 and will be removed
    in 0.7.0. Please switch to Hypercorn or an alternative ASGI
    Server. This section is kept for reference.

To use Gunicorn you must configure it to use a Quart Worker, is is
done by setting the ``worker-class`` to either
:class:`~quart.worker.GunicornWorker` or
:class:`~quart.worker.GunicornUVLoopWorker` and then informing
Gunicorn of the Quart app instance. For example with the code given
above you can deploy via,

.. code-block:: bash

    gunicorn --worker-class quart.worker.GunicornWorker example:app

All the standard Gunicorn settings apply and can be used, including
access log formatting.
