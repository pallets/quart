.. _server_sent_events:

Server Sent Events
==================

Quart supports streaming `Server Sent
Events<https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events>`_,
which you may decide to use as an alternative to WebSockets -
especially if the communication is one way.

Server sent events must be encoded in a specific way, as shown by this
helper class:

.. code-block:: python

    from dataclasses import dataclass

    @dataclass
    class ServerSentEvent:
        data: str
        event: str | None = None
        id: int | None = None
        retry: int | None

        def encode(self) -> bytes:
            message = f"data: {self.data}"
            if self.event is not None:
                message = f"{message}\nevent: {self.event}"
            if self.id is not None:
                message = f"{message}\nid: {self.id}"
            if self.retry is not None:
                message = f"{message}\nretry: {self.retry}"
            message = f"{message}\r\n\r\n"
            return message.encode('utf-8')

To use a GET route that returns a streaming generator is
required. This generator, ``send_events`` in the code below, must
yield the encoded Server Sent Event. The route itself also needs to
check the client will accept ``text/event-stream`` responses and set
the response headers appropriately:

.. code-block:: python

    from quart import abort, make_response

    @app.get("/sse")
    async def sse():
        if "text/event-stream" not in request.accept_mimetypes:
            abort(400)

        async def send_events():
            while True:
                data = ...  # Up to you where the events are from
                event = ServerSentEvent(data)
                yield event.encode()

        response = await make_response(
            send_events(),
            {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Transfer-Encoding': 'chunked',
            },
        )
        response.timeout = None
        return response

Quart by default will timeout long responses to protect against
possible denial of service attacks, see :ref:`dos_mitigations`. For
this reason the timeout is disabled. This can be done globally,
however that could make other routes DOS vulnerable, therefore the
recommendation is to set the timeout attribute on the specific
response to ``None``.
