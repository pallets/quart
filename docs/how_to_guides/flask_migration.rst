.. _flask_migration:

Migration from Flask
====================

As Quart is compatible with the Flask public API it should be
relatively straight forward to migrate to Quart from Flask. This
migration basically consists of two steps, firstly replacing Flask
imports with Quart imports and secondly inserting the relevant
``async`` and ``await`` keywords.

Import changes
--------------

Any import of a module from the flask package can be changed to be an
import from the same module in the quart package. For example the
following in Flask,

.. code-block:: python

    from flask import Flask, g, request
    from flask.helpers import make_response

becomes in Quart,

.. code-block:: python

    from quart import Quart, g, request
    from quart.helpers import make_response

noting that the imported objects have the same name in both packages
except for the ``Quart`` and ``Flask`` classes themselves.

This can largely be automated via the use of find and replace.

Async and Await
---------------

As Quart is an asynchronous framework based on asyncio, it is
necessary to explicitly add ``async`` and ``await`` keywords. The most
notable place in which to do this is route functions, for example the
following in Flask,

.. code-block:: python

    @app.route('/')
    def route():
        data = request.get_json()
        return render_template_string("Hello {{name}}", name=data['name'])

becomes in Quart,

.. code-block:: python

    @app.route('/')
    async def route():
        data = await request.get_json()
        return await render_template_string("Hello {{name}}", name=data['name'])

If you have sufficient test coverage it is possible to search for
awaitables by searching for ``RuntimeWarning: coroutine 'XX' was never
awaited``.

The following common lines require awaiting, note that these must be
awaited in functions/methods that are async. Awaiting in a non-async
function/method is a syntax error.

.. code-block:: python

    await request.data
    await request.get_data()
    await request.json
    await request.get_json()
    await request.form
    await request.files
    await render_template()
    await render_template_string()

Testing
-------

The test client also requires the usage of async and await keywords,
mostly to await test requests i.e.

.. code-block:: python

    await test_client.get('/')
    await test_client.post('/')
    await test_client.open('/', 'PUT')

Extensions
----------

To use a Flask extension with Quart see the :ref:`flask_extensions`
documentation.
