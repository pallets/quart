.. _quart_extensions:

Using Quart Extensions
======================

There are a number of extensions for Quart, some of which are listed
here,

- `Quart-Auth <https://github.com/pgjones/quart-auth>`_ Secure cookie
  sessions, allows login, authentication and logout.
- `Quart-Babel <https://github.com/Quart-Addons/quart-babel>`_ Implements i18n and l10n support for Quart.
- `Quart-Bcrypt <https://github.com/Quart-Addons/quart-bcrypt>`_ Provides bcrypt hashing utilities for your application.
- `Quart-compress <https://github.com/AceFire6/quart-compress>`_
  compress your application's responses with gzip.
- `Quart-compress2
  <https://github.com/DahlitzFlorian/quart-compress>`_ A package to
  compress responses in your Quart app with gzip .
- `Quart-CORS <https://github.com/pgjones/quart-cors>`_ Cross Origin
  Resource Sharing (access control) support.
- `Quart-DB <https://github.com/pgjones/quart-db>`_ Managed
  connection(s) to postgresql database(s).
- `Quart-events <https://github.com/smithk86/quart-events>`_ event
  broadcasting via WebSockets or SSE.
- `Quart-Login <https://github.com/0000matteo0000/quart-login>`_ a
  port of Flask-Login to work natively with Quart.
- `Quart-minify <https://github.com/AceFire6/quart_minify/>`_ minify
  quart response for HTML, JS, CSS and less.
- `Quart-Mongo <https://github.com/Quart-Addons/quart-mongo>`_  Bridges Quart, Motor, and Odmantic to create a powerful MongoDB
  extension.
- `Quart-Motor <https://github.com/marirs/quart-motor>`_ Motor
  (MongoDB) support for Quart applications.
- `Quart-OpenApi <https://github.com/factset/quart-openapi/>`_ RESTful
  API building.
- `Quart-Keycloak <https://github.com/kroketio/quart-keycloak>`_
  Support for Keycloak's OAuth2 OpenID Connect (OIDC).
- `Quart-Rapidoc <https://github.com/marirs/quart-rapidoc>`_ API
  documentation from OpenAPI Specification.
- `Quart-Rate-Limiter
  <https://github.com/pgjones/quart-rate-limiter>`_ Rate limiting
  support.
- `Quart-Redis
  <https://github.com/enchant97/quart-redis>`_ Redis connection handling
- `Webargs-Quart <https://github.com/esfoobar/webargs-quart>`_ Webargs
  parsing for Quart.
- `Quart-SqlAlchemy <https://github.com/joeblackwaslike/quart-sqlalchemy>`_ Quart-SQLAlchemy provides a simple wrapper for SQLAlchemy.
- `Quart-WTF <https://github.com/Quart-Addons/quart-wtf>`_ Simple integration of Quart
  and WTForms. Including CSRF and file uploading.
- `Quart-Schema <https://github.com/pgjones/quart-schema>`_ Schema
  validation and auto-generated API documentation.
- `Quart-session <https://github.com/sanderfoobar/quart-session>`_ server
  side session support.
- `Quart-LibreTranslate <https://github.com/Quart-Addons/quart-libretranslate>`_ Simple integration to
  use LibreTranslate with your Quart app.
- `Quart-Uploads <https://github.com/Quart-Addons/quart-uploads>`_ File upload handling for Quart.

Supporting sync code in a Quart Extension
-----------------------------------------

Extension authors can support sync functions by utilising the
:meth:`quart.Quart.ensure_async` method. For example, if the extension
provides a view function decorator add ``ensure_async`` before calling
the decorated function,

.. code-block:: python

    def extension(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ...  # Extension logic
            return await current_app.ensure_async(func)(*args, **kwargs)
        return wrapper
