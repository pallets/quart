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

Finally the flask_patching system also relies on patching asyncio, and
hence other implementations or event loop policies are unlikely to
work.

Supported extensions
--------------------

A list of officially supported flask extensions exist `here
<http://flask.pocoo.org/extensions/>`_ of those a few have been tested
against Quart (the extensions tested are still supported and don't
require external services). The following flask extensions are tested
and known to work with quart,

- `Flask-BCrypt <http://pythonhosted.org/Flask-Bcrypt/>`_
- `Flask-Caching <https://flask-caching.readthedocs.io/en/latest/>`_
- `Flask-KVSession <https://github.com/mbr/flask-kvsession>`_
- `Flask-Limiter <http://github.com/alisaifee/flask-limiter/>`_
- `Flask-Login <http://github.com/maxcountryman/flask-login/>`_
- `Flask-Mail <https://github.com/mattupstate/flask-mail>`_
- `Flask-Mako <http://github.com/benselme/flask-mako/>`_
- `Flask-Seasurf <https://github.com/maxcountryman/flask-seasurf/>`_
- `Flask-WTF <https://github.com/lepture/flask-wtf>`_

Broken extensions
-----------------

The following flask extensions have been tested are known not to work
with quart,

- `Flask-CORS <https://github.com/corydolphin/flask-cors>`_, as it
  uses ``app.make_response`` which must be awaited. Try `Quart-CORS
  <https://gitlab.com/pgjones/quart-cors>`_ instead.
- `Flask-Restful <https://github.com/flask-restful/flask-restful/>`_
  as it subclasses the Quart (app) class with synchronous methods
  overriding asynchronous methods. Try `Quart-OpenApi
  <https://github.com/factset/quart-openapi/>`_ instead.
- `Flask-SQLAlchemy <https://github.com/mitsuhiko/flask-sqlalchemy/>`_
  as it relies on thread isolation, which Quart does not support. Try
  `Databases <https://github.com/encode/databases>`_ instead.
