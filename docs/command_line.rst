.. _command_line:

Custom Command Line Commands
============================

The ``quart`` command can be customised by the app to add additional
functionality. A very typical use case is to add a database
initialisation command,

.. code-block:: python

    import click

    @app.cli.command()
    def initdb():
        click.echo('Database is migrating')
        ...

which will then work as,

.. code-block:: console

    $ quart initdb
    Database is migrating

.. note::

   Unlike Flask the Quart commands do not run within an app context,
   as click commands are synchronous rather than asynchronous.

Asynchronous usage
------------------

The best way to use some asynchronous code in a custom command is to
create an event loop and run it manually, for example,

.. code-block:: python

    import asyncio

    @app.cli.command()
    def fetch_db_data():
        result = asyncio.get_event_loop().run_until_complete(_fetch())


    async def _fetch():
        return await db.execute(...)
