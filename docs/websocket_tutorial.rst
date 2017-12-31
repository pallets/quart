.. blog_tutorial:

Tutorial: Websockets
====================

This tutorial will guide you through building the websocket server
present in the ``examples/websocket`` directory. This is a very simple
app that simply echos back all messages recieved over the websocket.

Running the example
'''''''''''''''''''

To run the example, in ``examples/websocket`` the following should start
the server, (see :ref:`installation` first),

.. code-block:: console

    $ export QUART_APP=websocket:app
    $ quart run

the websocket is then available at `http://localhost:5000/
<http://localhost:5000/>`_.

1: Structure
------------

Quart by default expects the code to be structured in a certain way in
order for templates and static file to be found. This means that you
should structure the websocket as follows,

::

    websocket/
    websocket/static/
    websocket/static/js/
    websocket/static/css/
    websocket/templates/

doing so will also make your project familiar to others, as you follow
the same convention.

2: Installation
---------------

It is always best to run python projects within a virtualenv, which
should be created and activated as follows, (Python 3.6 or better is
required),

.. code-block:: console

    $ cd websocket
    $ python -m venv venv
    $ source venv/bin/activate

for this websocket we will only need Quart, which should be installed,

.. code-block:: console

    (venv) $ pip install quart

.. Note::

   ``(venv)`` is used to indicate when the commands must be run within
   the virtualenv.

3: Websockets
-------------

`Websocket <https://www.w3.org/TR/websockets/>`_ connections allow for
continuous two way communication between a client and a server without
having to reopen or negotiate a connection. Chat systems and games are
two examples with continuous communication that are well suited to
websockets.

Quart natively supports websockets, and a simple websocket echo route
is,

.. code-block:: python

    from quart import websocket

    @app.websocket('/ws')
    async def ws():
        while True:
            data = await websocket.receive()
            await websocket.send(f"echo {data}")

Quart also makes testing websockets easy, as so,

.. code-block:: python

    @pytest.mark.asyncio
    async def test_websocket(app):
        test_client = app.test_client()
        data = b'bob'
        with test_client.websocket('/ws') as test_websocket:
            await test_websocket.send(data)
            result = await test_websocket.receive()
        assert result == data

4: Javascript
-------------

To connect to and communicate with a websocket in Javascript a
``WebSocket`` object must be used,

.. code-block:: javascript

    var ws = new WebSocket('ws://' + document.domain + ':' + location.port + '/ws');
    ws.onmessage = function (event) {
        console.log(event.data);
    };

    ws.send('bob');

5: Conclusion
-------------

The example files contain this entire tutorial and a little more, so
they are now worth a read. Hopefully you can now go ahead and create
your own apps that use websockets.
