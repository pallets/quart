.. _flask_evolution:

Flask evolution
===============

(The author) sees Quart as an evolution of Flask, primarily to support
asyncio and secondarily to support websockets and HTTP/2. These
additions are designed following (the author's interpretation) of
Flask's design choices. It is for this reason that the websocket
context and global exist, rather than as an argument to the route
handler.

Omissions from the Flask API
----------------------------

There are parts of the Flask API that I've decided to either not
implement, these are,

request.stream
~~~~~~~~~~~~~~

The ``stream`` method present on Flask request instances allows the
request body to be 'streamed' via a file like interface. In Quart
:ref:`request_body` is done differently in order to make use of the
``async`` keyword.
