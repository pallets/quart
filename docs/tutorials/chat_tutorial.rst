.. _chat_tutorial:

Tutorial: Building a basic chat server
======================================

In this tutorial we will build a very basic chat server. It will allow
anyone to send messages to everyone else currently connected to the
server.

This tutorial is meant to serve as an introduction to WebSockets in
Quart. If you want to skip to the end the code is on `Github
<https://github.com/pallets/quart/tree/main/examples/chat>`_.

1: Creating the project
-----------------------

We need to create a project for our chat server, I like to use `Poetry
<https://python-poetry.org>`_ to do this. Poetry is installed via pip
(or via `Brew <https://brew.sh/>`_):

.. code-block:: console

    pip install poetry

We can then use Poetry to create a new chat project:

.. code-block:: console

    poetry new --src chat

Our project can now be developed in the *chat* directory, and all
subsequent commands should be in run the *chat* directory.

2: Adding the dependencies
--------------------------

We only need Quart to build this simple chat server, which we can
install as a dependency of the project by running the following:

.. code-block:: console

    poetry add quart

Poetry will ensure that this dependency is present and the paths are
correct by running:

.. code-block:: console

    poetry install

3: Creating the app
-------------------

We need a Quart app to be our web server, which is created by the
following addition to *src/chat/__init__.py*:

.. code-block:: python
    :caption: src/chat/__init__.py

    from quart import Quart

    app = Quart(__name__)

    def run() -> None:
        app.run()

To make the app easy to run we can call the run method from a poetry
script, by adding the following to *pyproject.toml*:

.. code-block:: toml
    :caption: pyproject.toml

    [tool.poetry.scripts]
    start = "chat:run"

Which allows the following command to start the app:

.. code-block:: console

    poetry run start

4: Serving the UI
-----------------

When users visit our chat website we will need to show them a UI which
they can use to enter and receive messages. The following HTML
template should be added to *src/chat/templates/index.html*:

.. code-block:: html
    :caption: src/chat/templates/index.html

    <script type="text/javascript">
      const ws = new WebSocket(`ws://${location.host}/ws`);

      ws.addEventListener('message', function (event) {
        const li = document.createElement("li");
        li.appendChild(document.createTextNode(event.data));
        document.getElementById("messages").appendChild(li);
      });

      function send(event) {
        const message = (new FormData(event.target)).get("message");
        if (message) {
          ws.send(message);
        }
        event.target.reset();
        return false;
      }
    </script>

    <div style="display: flex; height: 100%; flex-direction: column">
      <ul id="messages" style="flex-grow: 1; list-style-type: none"></ul>

      <form onsubmit="return send(event)">
        <input type="text" name="message" minlength="1" />
        <button type="submit">Send</button>
      </form>
    </div>

This is a very basic UI both in terms of the styling, but also as
there is no error handling for the WebSocket.

We can now serve this template for the root path i.e. ``/`` by adding
the following to *src/chat/__init__.py*:

.. code-block:: python

    from quart import render_template

    @app.get("/")
    async def index():
        return await render_template("index.html")

5: Building a broker
--------------------

Before we can add the websocket route we need to be able to pass
messages from one connected client to another. For this we will need a
message-broker. To start we'll build our own in memory broker by
adding the following to *src/chat/broker.py*:

.. code-block:: python
    :caption: src/chat/broker.py

    import asyncio
    from typing import AsyncGenerator

    from quart import Quart

    class Broker:
        def __init__(self) -> None:
            self.connections = set()

        async def publish(self, message: str) -> None:
            for connection in self.connections:
                await connection.put(message)

        async def subscribe(self) -> AsyncGenerator[str, None]:
            connection = asyncio.Queue()
            self.connections.add(connection)
            try:
                while True:
                    yield await connection.get()
            finally:
                self.connections.remove(connection)

This ``Broker`` has a publish-subscribe pattern based interface, with
clients expected to publish messages to other clients whilst
subscribing to any messages sent.

6: Implementing the websocket
-----------------------------

We can now implement the websocket route, by adding the following to
*src/chat/__init__.py*:

.. code-block:: python
    :caption: src/chat/__init__.py

    import asyncio

    from quart import websocket

    from chat.broker import Broker

    broker = Broker()

    async def _receive() -> None:
        while True:
            message = await websocket.receive()
            await broker.publish(message)

    @app.websocket("/ws")
    async def ws() -> None:
        try:
            task = asyncio.ensure_future(_receive())
            async for message in broker.subscribe():
                await websocket.send(message)
        finally:
            task.cancel()
            await task

The ``_receive`` coroutine must run as a separate task to ensure that
sending and receiving run concurrently. In addition this task must be
properly cancelled and cleaned up.

When the user disconnects a CancelledError will be raised breaking the
while loops and triggering the finally blocks.

7: Testing
----------

To test our app we need to check that messages sent via the websocket
route are echoed back. This is done by adding the following to
*tests/test_chat.py*:

.. code-block:: python
    :caption: tests/test_chat.py

    import asyncio

    from quart.testing.connections import TestWebsocketConnection as _TestWebsocketConnection

    from chat import app

    async def _receive(test_websocket: _TestWebsocketConnection) -> str:
        return await test_websocket.receive()

    async def test_websocket() -> None:
        test_client = app.test_client()
        async with test_client.websocket("/ws") as test_websocket:
            task = asyncio.ensure_future(_receive(test_websocket))
            await test_websocket.send("message")
            result = await task
            assert result == "message"

As the test is an async function we need to install `pytest-asyncio
<https://github.com/pytest-dev/pytest-asyncio>`_ by running the
following:

.. code-block:: console

    poetry add --dev pytest-asyncio

Once installed it needs to be configured by adding the following to
*pyproject.toml*:

.. code-block:: toml

    [tool.pytest.ini_options]
    asyncio_mode = "auto"

Finally we can run the tests via this command:

.. code-block:: console

    poetry run pytest tests/

If you are running this in the Quart example folder you'll need to add
a ``-c pyproject.toml`` option to prevent pytest from using the Quart
pytest configuration.

8: Summary
----------

The message-broker we've built so far only works in memory, which
means that messages are only shared with users connected to the same
server instance. To share messages across server instances we need to
use a third party broker, such as redis via the `aioredis
<https://aioredis.readthedocs.io>`_ library which supports a pub/sub
interface.
