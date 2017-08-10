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


Supported extensions
--------------------

A list of officially supported flask extensions exist `here
<http://flask.pocoo.org/extensions/>`_ of those a few have been tested
against Quart (the extensions tested are still supported and don't
require external services). The following flask extensions are tested
and known to work with quart,

- `Flask-BCrypt <http://pythonhosted.org/Flask-Bcrypt/>`_
- `Flask-Caching <https://flask-caching.readthedocs.io/en/latest/>`_
- `Flask-Limiter <http://github.com/alisaifee/flask-limiter/>`_
- `Flask-Login <http://github.com/maxcountryman/flask-login/>`_
- `Flask-Mako <http://github.com/benselme/flask-mako/>`_
- `Flask-Seasurf <https://github.com/maxcountryman/flask-seasurf/>`_
- `Flask-WTF <https://github.com/lepture/flask-wtf>`_

Broken extensions
-----------------

The following flask extensions have been tested are known not to work
with quart,

- `Flask-CORS <https://github.com/corydolphin/flask-cors>`_, as it
  uses ``app.make_response`` which must be awaited.
- `Flask-Restful <https://github.com/flask-restful/flask-restful/>`_
  as it requires an Accept header datastructure present in Werkzeug
  and missing in Quart.
