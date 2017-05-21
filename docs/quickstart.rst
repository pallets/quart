.. _quickstart:

Quickstart
==========


Hello World
-----------

.. code-block:: python

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def hello():
        return 'hello'

    app.run()
