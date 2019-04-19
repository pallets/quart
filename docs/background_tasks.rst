.. _background_tasks:

Background tasks
================

Some actions can often take a lot of time to complete, which may cause
the client to timeout before receiving a response. Equally some tasks
just don't need to be completed before the response is sent and
instead can be done in the background. Asyncio provides functionality
to run tasks like these in the background, however care must be taken
if the task is CPU heavy.

In the below example two background tasks will be created, one that
runs in the same thread (and event loop) as the Quart server and
another that runs on a separate thread. CPU heavy tasks should run on
a separate thread via the ``run_in_executor`` function.

.. code-block:: python

    async def io_background_task():
        ...

    async def cpu_background_task():
        ...

    @app.route('/jobs/', methods=['POST'])
    async def create_job():
        # Runs in this event loop
        asyncio.ensure_future(io_background_task())

        # Runs on another thread
        asyncio.get_running_loop().run_in_executor(None, cpu_background_task())
        return 'Success'

These background tasks will not have access to the request or app
context, unless the copy functions are used, see :ref:`contexts`.

.. warning::

    As Quart is based on asyncio it will run on a single execution and
    switch between tasks as they become blocked on waiting on IO, if a
    task does not need to wait on IO it will instead block the event
    loop and Quart could become unresponsive. Additionally the task
    will consume the same CPU resources as the server and hence could
    slow the server.
