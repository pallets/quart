.. _flask_extensions:

Using Flask Extensions
======================

Flask extensions can be used with Quart, with some caveats. To do so
the very first import in your code must be ``import quart.flask_ext``
as this will add modules proporting to be Flask modules for later use
by the extension. For example,

.. code-block:: python

    import quart.flask_ext

    from quart import Quart
    import flask_login

    app = Quart(__name__)
    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)

    ...


Caveats
-------

Flask extensions that try to access some parts of the request body
will fail, as these methods are asynchronous - only the form and file
properties are available in a synchronous form. To enable this the
request body must be fully received before any part of the request is
handled, which is a limitation not present in vanilla flask.

Trying to use Flask alongside Quart in the same runtime will likely not
work, and lead to surprising errors.
