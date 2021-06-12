.. _middleware:

Middleware
==========

Middleware can be used to wrap a Quart app instance and alter the ASGI
process. A very simple example would be to reject requests based on
the presence of a header,

.. code-block:: python

    class RejectMiddleware:

        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if "headers" not in scope:
                return await self.app(scope, receive, send)

            for header, value in scope['headers']:
                if header == 'X-Secret' and value == 'very-secret':
                    return await self.app(scope, receive, send)

            return await self.error_response(receive, send)

        async def error_response(self, receive, send):
            await send({
                'type': 'http.response.start',
                'status': 401,
                'headers': [(b'content-length', b'0')],
            })
            await send({
                'type': 'http.response.body',
                'body': b'',
                'more_body': False,
            })

Whilst middleware can always be used as a wrapper around the app
instance, it is best to assign to and wrap the ``asgi_app`` attribute,

.. code-block:: python

    quart_app.asgi_app = RejectMiddleware(quart_app.asgi_app)

as this ensures that the middleware is applied in any test code.

You can combine multiple middleware wrappers,

.. code-block:: python

    quart_app.asgi_app = RejectMiddleware(quart_app.asgi_app)
    quart_app.asgi_app = AdditionalMiddleware(quart_app.asgi_app)

and use any ASGI middleware.

.. warning::

    Middleware runs before any Quart code, which means that if the
    middleware returns a response no Quart functionality nor any Quart
    extensions will run.
