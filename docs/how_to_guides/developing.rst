.. _developing:

Developing with Quart
=====================

When developing it is best to have your Quart app running so you can
test any changes you make directly. This is made easier by the
reloader which reloads your app whenever a file is changed. The
reloader is active if you use ``app.run()``, ``quart run`` command or
``run_task`` method.


Quart run
---------

The ``quart run`` command is the recommended way to develop with Quart
and will run whichever app is specified by the ``QUART_APP``
environment variable. For example,

.. code-block:: python
    :caption: run.py

    from quart import Quart

    app = Quart(__name__)

    ...

.. code-block:: console

    $ QUART_APP=run:app quart run

The ``quart run`` command comes with ``--host``, and ``--port`` to
specify where the app is served, and ``--certfile`` and ``--keyfile``
to specify the SSL certificates to use.

app.run()
---------

The Quart class, instances typically named ``app``, has a
:meth:`~quart.Quart.run` method. This method runs a development server,
automatically turning on debug mode and code reloading. This can be
used to run the app via this snippet,

.. code-block:: python
    :caption: run.py

    from quart import Quart

    app = Quart(__name__)

    ...

    if __name__ == "__main__":
        app.run()

with the ``if`` ensuring that this code only runs if the file is run
directly, i.e.

.. code-block:: console

    $ python run.py

which ensures that it doesn't run in production.

The :meth:`~quart.Quart.run` method has options to set the ``host``,
and ``port`` the app will be served over, to turn off the reloader via
``use_reloader=False``, and to add specify SSL certificates via the
``certfile`` and ``keyfile`` options.

.. note::

   The :meth:`~quart.Quart.run` method will create a new event loop,
   use ``run_task`` instead if you wish to control the event loop.

app.run_task
------------

The Quart class also has a :meth:`~quart.Quart.run_task` method with
the same options as the :meth:`~quart.Quart.run` method. The
``run_task`` returns an asyncio task that when awaited will run the
app. This is as useful as it makes no alterations to the event
loop. The ``run_task`` can be used as so,

.. code-block:: python
    :caption: run.py

    import asyncio

    from quart import Quart

    app = Quart(__name__)

    ...

    if __name__ == "__main__":
        asyncio.run(app.run_task())

with the ``if`` ensuring that this code only runs if the file is run
directly, i.e.

.. code-block:: console

    $ python run.py

which ensures that it doesn't run in production.


Curl
----

To test the app locally I like to use a web browser, and the curl
command line tool. I'd recommend reading the curl `documentation
<https://curl.se/docs/>`_ and always using the ``-v``, ``--verbose``
option. For example,

.. code-block:: console

    $ curl -v localhost:5000/
