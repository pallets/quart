.. _dos_mitigations:

Denial Of Service mitigations
=============================

There are multiple ways a client can overload a server and deny
service to other clients. A simple example can simply be to call an
expensive route at a rate high enough that the server's resources are
exhausted. Whilst this could happen innocently (if a route was
popular) it takes a lot of client resource, there are malicious
methods to exhaust server resources.

There are two attack methods mitigated and discussed here, the first
aims to open as many connections to the server as possible without
freeing them, thereby eventually exhausting all the connections and
preventing other clients from connecting. As most request response
cycles last milliseconds before the connection is closed the key is to
somehow hold the connection open.

The second aims to exhaust the server's memory and hence either slow
the server to a crawl or kill the server application, thereby
preventing the server from replying to other clients. The key here is
to somehow make the server write a lot of information to memory.

Inactive connection
-------------------

This attack is of the first type and aims to exhaust the server's
connections. It works by opening connections to the server and then
doing nothing with the connection. A poorly configured server would
simply wait for the client to do something therefore holding the
connection open.

It is up to the ASGI server to guard against this attack, typically
via a configurable keep alive or timeout setting.

Large request body
------------------

This attack is of the second type and aims to exhaust the server's
memory by inviting it to receive a large request body (and hence write
the body to memory). A poorly configured server would have no limit on
the request body size and potentially allow a single request to
exhaust the server.

To mitigate this Quart limits the request body size to the value set
in the application config['MAX_CONTENT_LENGTH']. Any request with a
body larger than this limit will trigger a Request Entity Too Large,
413, response.

The default value for MAX_CONTENT_LENGTH is 16 MB, which is chosen as
it is the limit discussed in the Flask documentation.

Technically this limit refers to the maximum amount of data Quart will
allow in memory for a request body. This allows larger bodies to be
received and consumed if desired. The key being that the data is
consumed and not otherwise stored in memory. An example is,

.. code-block:: python

    async def route():
        async for data in request.body:
            # Do something with the data
            ...

it is advisable to add a timeout within each chunk if streaming the
request.

Slow request body
-----------------

This attack is of the first type and aims to exhaust the server's
connections by inviting it to wait a long time for the request's
body. A poorly configured server would wait indefinitely for the
request body.

To mitigate this Quart by default will not wait for the request body,
allowing the route handler to response if possible, for example if the
request does not have the correct authorisation. If the body is
needed, then the application config['BODY_TIMEOUT'] defines the number
of seconds to wait for the body to be completely received. If the
timeout is exhausted Quart would respond with RequestTimeout, 408.

The default value is 60 seconds, which is chosen as it is the typical
default timeout value.

Technically the timeout is only applied to the Response data methods
(get_data, data, json, get_json, form, and files) and not the body
attribute. This allows for known streaming requests to be consumed
as desired, see :ref:`request_body`.

No response consumption
-----------------------

This attack is of the second type and aims to exhaust the server's
memory by failing to consume the data sent to the client. This failure
results in backpressure on the server that leads to the response being
written to memory rather than the connection. A poorly configured
server would ignore the backpressure and exhaust its memory. (Note
this requires a route that responds with a lot of data, e.g. video
streaming).

It is up to the ASGI server to guard against this attack.

Slow response consumption
-------------------------

This attack is of the first type and aims to exhaust the server's
connections by inviting the server to take a long time sending the
response, for example by applying backpressure indefinitely. A poorly
configured server would simply wait indefinitely trying to send the
response.

To mitigate this Quart will limit the time it will try to send the
response to that set in the application config['RESPONSE_TIMEOUT'].
If this time is exhausted the connection is closed abruptly.

The default value is 60 seconds, which is chosen as it is the typical
default timeout value.

Technically this limit can be configured per response if desired,
e.g. if there is a single route that returns large files. This is an
example how,

.. code-block:: python

    async def route():
        response = await make_response(...)
        response.timeout = 120
        return response

Large websocket message
-----------------------

This attack is of the second type and aims to exhaust the server's
memory by inviting it to receive very large websocket messages. A
poorly configured server would have no limit on the message size
and potentially allow a single message to exhaust the server.

It is up to the ASGI server to guard against the attack.
