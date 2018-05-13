.. _asgi_deployments:

ASGI Deployments
================

The recommended way to deploy Quart is with Gunicorn as explained in
:ref:`deployment`, however it is possible to deploy Quart with an ASGI
server. A good example of which would be `Uvicorn
<https://github.com/encode/uvicorn>`_. To do so requires the Quart
instance (typically called ``app``) to be wrapped in a ASGIServer as
so

.. code-block:: python

    from quart import Quart
    from quart.serving import ASGIServer

    app = Quart(__name__)
    ...
    asgi_app = ASGIServer(app)

An ASGI server can then be used by referencing the ``asgi_app``, for
example if the above code is in a file called ``run.py`` uvicorn can
be used as so

.. code-block:: sh

    $ uvicorn run:asgi_app
