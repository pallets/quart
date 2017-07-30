.. _flask_extensions:

Using Flask Extensions
======================

Flask extensions can be used with Quart, with some caveats. To do so
the very first import in your code must be ``import quart.flask_patch``
as this will add modules proporting to be Flask modules for later use
by the extension. For example,

.. code-block:: python

    import quart.flask_patch

    from quart import Quart
    import flask_login

    app = Quart(__name__)
    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)

    ...


Caveats
-------

Flask extensions must use the global request proxy variable to access
the request, any other access e.g. via
:meth:`~quart.local.LocalProxy._get_current_object` will require
asynchronous access. To enable this the request body must be fully
received before any part of the request is handled, which is a
limitation not present in vanilla flask.

Trying to use Flask alongside Quart in the same runtime will likely not
work, and lead to surprising errors.

Note that the flask extension must be limited to creating routes,
using the request and rendering templates. Any other more advanced
functionality may not work.
