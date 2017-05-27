.. _quickstart:

Quickstart
==========

Hello World
-----------

A very simple app that simply returns a response containing ``hello``
is, (file ``hello-world.py``)

.. code-block:: python

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def hello():
        return 'hello'

    app.run()

and is simply run via

.. code-block:: sh

    python hello-world.py

and tested by

.. code-block:: sh

    curl localhost:5000
