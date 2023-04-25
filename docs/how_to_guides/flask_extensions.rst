.. _flask_extensions:

Using Flask Extensions
======================

Flask extensions can be used with Quart, with some caveats. To do so
the very first import in your code must be ``import quart.flask_patch``
as this will add modules purporting to be Flask modules for later use
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

The flask extension must be limited to creating routes, using the
request and rendering templates. Any other more advanced functionality
may not work.

Synchronous functions will not run in a separate thread (unlike Quart
normally) and hence may block the event loop.

Finally the flask_patching system also relies on patching asyncio, and
hence other implementations or event loop policies are unlikely to
work.

Supported extensions
--------------------

The following flask extensions are tested
and known to work with quart,

- `Flask-BCrypt <https://flask-bcrypt.readthedocs.io>`_
- `Flask-Caching <https://flask-caching.readthedocs.io>`_
- `Flask-KVSession <https://github.com/mbr/flask-kvsession>`_
- `Flask-Limiter <https://github.com/alisaifee/flask-limiter/>`_
- `Flask-Login <https://github.com/maxcountryman/flask-login/>`_ See
  also `Quart-Login <https://github.com/0000matteo0000/quart-login>`_
- `Flask-Mail <https://pythonhosted.org/Flask-Mail/>`_
- `Flask-Mako <https://pythonhosted.org/Flask-Mako/>`_
- `Flask-Seasurf <https://github.com/maxcountryman/flask-seasurf/>`_
- `Flask-SQLAlchemy <https://flask-sqlalchemy.palletsprojects.com>`_
- `Flask-WTF <https://flask-wtf.readthedocs.io>`_

Broken extensions
-----------------

The following flask extensions have been tested are known not to work
with quart,

- `Flask-CORS <https://github.com/corydolphin/flask-cors>`_, as it
  uses ``app.make_response`` which must be awaited. Try `Quart-CORS
  <https://github.com/pgjones/quart-cors>`_ instead.
- `Flask-Restful <https://flask-restful.readthedocs.io>`_
  as it subclasses the Quart (app) class with synchronous methods
  overriding asynchronous methods. Try `Quart-OpenApi
  <https://github.com/factset/quart-openapi/>`_ or `Quart-Schema
  <https://github.com/pgjones/quart-schema>`_ instead.


Reference
---------

More information about Flask extensions can be found
`here <https://flask.palletsprojects.com/extensions>`_.
