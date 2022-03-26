.. _configuration:

Configuration
=============

A common pattern is to store configuration values in the
environment. Quart supports this via
:meth:`~quart.Config.from_prefixed_env` which can be used to load
environment variables into the configuration. Only environment
variables starting with the prefix, default ``QUART_`` will be
loaded. For example if the environment variable ``QUART_TESTING=true``
is set then,

.. code-block:: python

    app = Quart(__name__)
    app.config.from_prefixed_env()
    assert app.config["TESTING"] is True

Another common pattern for configuration loading is to use class
inheritance to define common settings with production and development
overrides, for example,

.. code-block:: python

    class Config:
        DEBUG = False
        TESTING = False
        SECRET_KEY = 'secret'

    class Development(Config):
        DEBUG = True

    class Production(Config):
        SECRET_KEY = 'an actually secret key'

This can then be loaded in say a ``create_app`` function, for example:

.. code-block:: python

    def create_app(mode='Development'):
        """In production create as app = create_app('Production')"""
        app = Quart(__name__)
        app.config.from_object(f"config.{mode}")
        return app

Custom configuration class
--------------------------

The :attr:`~quart.Quart.config_class` can be set to a custom class,
however it must be changed before the app is initialised as the
:meth:`~quart.Quart.make_config` is called on construction.

Instance folders
----------------

An instance folder is a deployment specific location to store files
and configuration settings. As opposed to loading files relative to
the app root path :meth:`~quart.Quart.open_resource` you can load
files relative to an instance path
:meth:`~quart.Quart.open_instance_resource` including the
configuration. To load the configuration from this folder, instead of
relative to the app root path simply provide the
``instance_relative_config`` argument as ``True`` when initialising
the app ``app = Quart(__name__, instance_relative_config=True)``.

The instance path can be specified when initialising the app, or found
automatically if it exists. The search locations are::

    /app.py
    /instance/

or if the app has been installed::

    $PREFIX/var/app-instance/
