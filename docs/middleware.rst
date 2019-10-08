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

        def __call__(self, scope):
            for header, value in scope['headers']:
                 if header == 'X-Secret' and value == 'very-secret':
                     return self.app(scope)
            return self.error_response

        def error_response(self, receive, send):
            await send({
                'type': 'http.response.start',
                'status': 401,
                'headers': ['content-length', '0'],
            })
            await send({
                'type': 'http.response.body',
                'body': b'',
                'more_body': False,
            })

     quart_app.asgi_app = RejectMiddleware(quart_app.asgi_app)

This can then be extended and used with any ASGI Middleware and served
with any ASGI server.
