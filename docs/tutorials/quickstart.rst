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

.. code-block:: console

    python hello-world.py

or alternatively

.. code-block:: console

    $ export QUART_APP=hello-world:app
    $ quart run

and tested by

.. code-block:: sh

    curl localhost:5000

See also
--------

:ref:`cheatsheet`
