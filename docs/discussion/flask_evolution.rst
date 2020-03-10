.. _flask_evolution:

Flask evolution
===============

(The author) sees Quart as an evolution of Flask, primarily to support
asyncio and secondarily to support websockets and HTTP/2. These
additions are designed following (the author's interpretation) of
Flask's design choices. It is for this reason that the websocket
context and global exist, rather than as an argument to the route
handler. The details of HTTP/2 are also abstracted into the serving
layer allowing Quart to remain a micro framework.
