.. _background_tasks:

Background tasks
================

Some actions can often take a lot of time to complete, which may cause
the client to timeout before receiving a response. Equally some tasks
just don't need to be completed before the response is sent and
instead can be done in the background. Quart provides a way to create
and run a task in the background via the app ``add_background_task``
method,

.. code-block:: python

    async def background_task():
        ...

    @app.route('/jobs/', methods=['POST'])
    async def create_job():
        app.add_background_task(background_task)
        return 'Success'

The background tasks will have access to the app context. The tasks
will be awaited during shutdown to ensure they complete before the app
shutdowns.

.. warning::

    As Quart is based on asyncio it will run on a single execution and
    switch between tasks as they become blocked on waiting on IO, if a
    task does not need to wait on IO it will instead block the event
    loop and Quart could become unresponsive. Additionally the task
    will consume the same CPU resources as the server and hence could
    slow the server.


Testing background tasks
------------------------

The background task coroutine function can be tested by creating an
app context and await the function,

.. code-block:: python

    @pytest.mark.asyncio
    async def test_background_task():
        async with app.app_context():
            await background_task()
        assert something_to_test
