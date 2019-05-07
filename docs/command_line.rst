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

Including a CLI Command in an extension or another module
---------------------------------------------------------

To include CLI commands in a Quart extension or blueprint, register the methods in the "run" factory function

.. code-block:: python

    from quart import Quart
    from my_extension import my_cli

    def create_app():
        app = Quart(__name__)
        app = my_cli(app)
        return app

And in your module or extension:

.. code-block:: python

    import click

    def my_cli(app):
        # @click.option("--my-option")
	@app.cli.command("mycli")
	def my_cli_command():
            print("quart ran this command")

        return app

This can be run with:

.. code-block:: console

    $ quart mycli
    $ quart ran this command
