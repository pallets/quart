.. _sync_code:

Run synchronous code
====================

Synchronous code will block the event loop and degrade the performance
of the Quart application it is run in. This is because the synchronous
code will block the task it is run in and in addition block the event
loop. It is for this reason that synchronous code is best avoided,
with asynchronous versions used in preference.

It is likely though that you will need to use a third party library
that is synchronous as there is no asynchronous version to use in its
place. In this situation it is common to run the synchronous code in a
thread pool executor so that it doesn't block the event loop and hence
degrade the performace of the Quart application. This can be a bit
tricky to do, so Quart provides some helpers to do so. Firstly any
synchronous route will be run in an executor, i.e.

.. code-block:: python

    @app.route("/")
    def sync():
        method = request.method
        ...

will result in the sync function being run in a thread. Note that you
are still within the :ref:`contexts`, and hence you can still access
the ``request``, ``current_app`` and other globals.

The following functionality accepts syncronous functions and will run
them in a thread,

- Route handlers
- Endpoint handlers
- Error handlers
- Context processors
- Before request
- Before websocket
- Before first request
- Before serving
- After request
- After websocket
- After serving
- Teardown request
- Teardown websocket
- Teardown app context
- Open session
- Make null session
- Save session

Context usage
-------------

Whilst you can access the ``request`` and other globals in synchronous
routes you will be unable to await coroutine functions. To work around
this Quart provides :meth:`~quart.app.Quart.run_sync` which can be
used as so,

.. code-block:: python

    @app.route("/")
    async def sync_within():
        data = await request.get_json()

        def sync_processor():
             # does something with data
             ...

        result = await run_sync(sync_processor)()
        return result

this is similar to utilising the asyncio run_in_executor function,

.. code-block:: python

    @app.route("/")
    async def sync_within():
        data = await request.get_json()

        def sync_processor():
             # does something with data
             ...

        result = await asyncio.get_running_loop().run_in_exector(
            None, sync_processor
        )
        return result

.. note::

   The run_in_executor function does not copy the current context,
   whereas the run_sync method does. It is for this reason that the
   latter is recommended. Without the copied context the ``request``
   and other globals will not be accessible.
