.. _quart_extensions:

Using Quart Extensions
======================

There are a number of extensions for Quart, some of which are listed
here,

- `Quart-Auth <https://gitlab.com/pgjones/quart-auth>`_ Secure cookie
  sessions, allows login, authentication and logout.
- `Quart-compress <https://github.com/AceFire6/quart-compress>`_
  compress your application's responses with gzip.
- `Quart-compress2
  <https://github.com/DahlitzFlorian/quart-compress>`_ A package to
  compress responses in your Quart app with gzip .
- `Quart-CORS <https://gitlab.com/pgjones/quart-cors>`_ Cross Origin
  Resource Sharing (access control) support.
- `Quart-events <https://github.com/smithk86/quart-events>`_ event
  broadcasting via WebSockets or SSE.
- `Quart-minify <https://github.com/AceFire6/quart_minify/>`_ minify
  quart response for HTML, JS, CSS and less.
- `Quart-Motor <https://github.com/marirs/quart-motor>`_ Motor
  (MongoDB) support for Quart applications.
- `Quart-OpenApi <https://github.com/factset/quart-openapi/>`_ RESTful
  API building.
- `Quart-Rapidoc <https://github.com/marirs/quart-rapidoc>`_ API
  documentation from OpenAPI Specification.
- `Quart-Rate-Limiter
  <https://gitlab.com/pgjones/quart-rate-limiter>`_ Rate limiting
  support.
- `Webargs-Quart <https://github.com/esfoobar/webargs-quart>`_ Webargs
  parsing for Quart.
- `Quart-Schema <https://gitlab.com/pgjones/quart-schema>`_ Schema
  validation and auto-generated API documentation.
- `Quart-session <https://github.com/xmrdsc/quart-session>`_ server
  side session support.


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
            return await current_app.ensure_sync(func)(*args, **kwargs)
        return wrapper
