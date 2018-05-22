.. broadcast_tutorial:

Tutorial: Broadcast Server Side Events
======================================

This tutorial will guide you through building the broadcast server
side event example present in the ``examples/broadcast``
directory. This is a very simple app that broadcasts any message sent
to it to every connected client.

Running the example
'''''''''''''''''''

To run the example, in ``examples/broadcast`` the following should start
the server, (see :ref:`installation` first),

.. code-block:: console

    $ export QUART_APP=broadcast:app
    $ quart run

the broadcast is then available at `http://localhost:5000/
<http://localhost:5000/>`_.

1: Structure
------------

Quart by default expects the code to be structured in a certain way in
order for templates and static file to be found. This means that you
should structure the broadcast as follows,

::

    broadcast/
    broadcast/static/
    broadcast/static/js/
    broadcast/static/css/
    broadcast/templates/

doing so will also make your project familiar to others, as you follow
the same convention.

2: Installation
---------------

It is always best to run python projects within a virtualenv, which
should be created and activated as follows, (Python 3.6 or better is
required),

.. code-block:: console

    $ cd broadcast
    $ pipenv install quart

for this broadcast we will only need Quart. Now pipenv can be activated,

.. code-block:: console

    $ pipenv shell

3: Server Sent Events
---------------------

`Server Sent Events <https://www.w3.org/TR/eventsource/>`_, or SSEs,
or EventSource (in Javascript), are an extension to HTTP that allow a
client to keep a connection open to a server thereby allowing the
server to send events to the client as it chooses.

Server sent events have a specific structure consisting at the minimum
of some string data and optionally an event, id and or retry tag. To
send this structured data the following class can be used,

.. code-block:: python

    class ServerSentEvent:

        def __init__(
                self,
                data: str,
                *,
                event: Optional[str]=None,
                id: Optional[int]=None,
                retry: Optional[int]=None,
        ) -> None:
            self.data = data
            self.event = event
            self.id = id
            self.retry = retry

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

with the route itself returning an asynchronous generator with the
correct headers, as so,

.. code-block:: python

    @app.route('/sse')
    async def sse():
        async def send_events():
            ...
            event = ServerSentEvent(data)
            yield event.encode()

        return send_events(), {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        }

the asynchronous generator then yields server sent events.

4: Javascript equivalent
------------------------

In order to recieve server sent events in the browser the Javascript
must declare and use an ``EventSource`` object, like so,

.. code-block:: javascript

    var es = new EventSource('/sse');
    es.onmessage = function (event) {
        var messages_dom = document.getElementsByTagName('ul')[0];
        var message_dom = document.createElement('li');
        var content_dom = document.createTextNode('Received: ' + event.data);
        message_dom.appendChild(content_dom);
        messages_dom.appendChild(message_dom);
    };

with the above adding each new message as a list item.

5: All together
---------------

To complete the app we need to accept messages and then broadcast them
to every client. The latter part is best achieved by each client
having its own Queue which it receives messages on before broadcasting
them. The following snippet acheives this,

.. code-block:: python

    app.clients = set()

    @app.route('/', methods=['POST'])
    async def broadcast():
        data = await request.get_json()
        for queue in app.clients:
            await queue.put(data['message'])
        return jsonify(True)

    @app.route('/sse')
    async def sse():
        queue = asyncio.Queue()
        app.clients.add(queue)
        async def send_events():
            while True:
                data = await queue.get()
                event = ServerSentEvent(data)
                yield event.encode()

        return send_events(), {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        }

6: Conclusion
-------------

The example files contain this entire tutorial and a little more, so
they are now worth a read. Hopefully you can now go ahead and create
your own apps that use Server Sent Events.
