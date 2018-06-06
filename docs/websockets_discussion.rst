.. _websockets_discussion:

Websockets
==========

Websockets start as a GET request that can either be upgraded to a
websocket via a 101, switching protocols, response or any other
response. The choice of what to do, or how to respond, is often not
possible in other frameworks and is one of the motivating aims in
Quart. In addition as websockets are very similar to requests, Quart
aims to have analogues functionality between websockets and requests.

Request analogues
-----------------

Websockets are very similar to GET requests, to the extent that is was
tempting to simply extend the Flask request API to include websocket
functionality. This would likely cause surprise to users of
Flask-Sockets or Flask-SocketIO which set the de-facto Flask
standard. Therefore I decided to introduce the websocket functionality
alongside the existing request functionality.

As websockets are so similar to GET requests it makes sense to produce
an analogue for all the functionality available for requests. For
example. :meth:`~quart.app.Quart.before_request` and
:meth:`~quart.app.Quart.before_websocket` and there is a *websocket
context* alongside the *request context*.

Response or Upgrade
-------------------

The utility of being able to choose how to respond, or whether to
upgrade, is best shown when considering authentication. In the example
below a typical login_required decorator can be used to prevent
unauthorised usage of the websocket.

.. code-block:: python

    def login_required(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if websocket.authentication == (...):
                return await func(*args, **kwargs)
            else:
                abort(401)
        return wrapper

    @app.websocket('/ws')
    @login_required
    async def ws():
        while True:
            await websocket.receive()
            ...

Quart also allows for the acceptance response (101) to be manually
sent via :meth:`~quart.wrappers.Websocket.accept` as this gives the
framework user full control.

.. note::

    This functionality is only useable with ASGI servers that
    implement the ``Websocket Denial Response`` extension. If the
    server does not support this extension Quart will instruct the
    server to close the connection without a response. Hypercorn, the
    recommended ASGI server, supports this extension.
