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

    quart_app.asgi_app = RejectMiddleware(quart_app.asgi_app)

This can then be extended and used with any ASGI Middleware and served
with any ASGI server.

.. warning::

    Middleware runs before any Quart code, which means that if the
    middleware returns a response no Quart functionality nor any Quart
    extensions will run.
