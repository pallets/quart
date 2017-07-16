.. _async_compatibility:

Async compatibility
===================

Synchronous and asynchronous code are not directly compatible in that
the functions must be called differently depending on the type. This
limits what can be done, for example in how Quart interacts with Flask
extensions and any effort to make Flask directly asynchronous.

In my opinion it is much easier to start with an asynchronous codebase
that calls synchronous code than vice versa in Python. I will try and
reason why below.

Calling sync code from async functions
--------------------------------------

This is mostly easy in that you can either call, or via a simple wrapper
await a synchronous function,

.. code-block:: python

    async def example():
        sync_call()
        await asyncio.coroutine(sync_call)()

whilst this doesn't actually change the nature, the call is
synchronous, it does work.

Calling async code from sync functions
--------------------------------------

This is where things get difficult, as it is only possible to create a
single event loop. Hence this can only be used once,

.. code-block:: python

    def example():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_call())

therefore if you are not at the very outer scope it isn't really
possible to call asynchronous code from a synchronous function.

This is problematic when dealing with Flask extensions as for example the
extension may have something like,

.. code-block:: python

    @app.route('/')
    def route():
        data = request.form
        return render_template_string("{{ name }}", name=data['name'])

whilst the route function can be wrapped with the
``asyncio.coroutine`` function and hence awaited, there is no (easy?)
way to insert the ``await`` before the ``request.form`` and
``render_template`` calls.

It is for this reason that a proxy object,
:class:`~quart.flask_ext.globals.FlaskRequestProxy`, and render,
:func:`~quart.flask_ext.templating.render_template` functions are
created for the Flask extensions. The former adding synchronous
request methods and the other providing synchronous functions.

Quart monkey patches a ``sync_wait`` method onto the base event loop
allowing for definitions such as,

.. code-block:: python

    from quart.templating import render_template as quart_render_template

    def render_template(*args):
        return asyncio.sync_wait(quart_render_template(*args))
