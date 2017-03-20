Quart
=====

|Build Status|

Quart is a microframework for Python based on Flask and asyncio.

Quickstart
----------

.. code-block::

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def hello():
        return 'hello'

    app.run()

API Compatibility with Flask
----------------------------

The Flask API can be described as consisting of the Flask public and
private API and Werkzeug upon which Flask is based. Quart is designed
to be fully compatible with the Flask public API (aside from async and
await keywords). Thereafter the aims is to be mostly compatible with
the Flask private API and without guarantees with the Werkzeug API.

Migrating from Flask
~~~~~~~~~~~~~~~~~~~~

It should be possible to migrate to Quart from Flask by a find and
replace of ``flask`` to ``quart`` and then adding ``async`` and
``await`` keywords.

Known differences
~~~~~~~~~~~~~~~~~

* There is no ``getlist`` method on the ``request.args`` object,
  rather ``getall`` should be used instead.


Design decisions
----------------

The asyncio callback ``create_server`` approach is faster than the
streaming ``start_server`` approach, and hence is used. This is based
on benchmarking and the `uvloop <https://github.com/MagicStack/uvloop>`_
research.

Deploying
---------

This isn't ready for production. To deploy use gunicorn as follows
``gunicorn --worker-class quart.worker.GunicornWorker ...`` or
``gunicorn --worker-class quart.worker.GunicornUVLoopWorker ...``.


.. |Build Status| image:: https://gitlab.com/pgjones/quart/badges/master/build.svg
   :target: https://gitlab.com/pgjones/quart/commits/master
