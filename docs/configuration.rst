.. _configuration:

Configuration
=============

A common pattern for configuration loading is to use class inheritance
to define common settings with production and development overrides,
for example,

.. code-block:: python

    class Config:
        DEBUG = False
        TESTING = False
        SECRET_KEY = 'secret'

    class Development(Config):
        DEBUG = True

    class Production(Config):
        SECRET_KEY = 'an actually secret key'

This can then be loaded in say a create_app function
(factory_pattern_), for example,

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
