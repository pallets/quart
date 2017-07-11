.. _deployment:

Deploying Quart
===============

It is not recommended to run Quart directly (via the
:meth:`~quart.app.Quart.run`) in production. Instead it is recommended
that Quart be run via `Gunicorn <http://gunicorn.org/>`_.

To use Gunicorn you must configure it to use a Quart Worker, is is
done by setting the ``worker-class`` to either
:class:`~quart.worker.GunicornWorker` or
:class:`~quart.worker.GunicornUVLoopWorker` and then informing
Gunicorn of the Quart app instance. For example for a file called,
``example.py``, containing

.. code-block:: python

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def hello():
        return 'Hello World'

you can deploy via,

.. code-block:: bash

    gunicorn --worker-class quart.worker.GunicornWorker example:app

All the standard Gunicorn settings apply and can be used.
