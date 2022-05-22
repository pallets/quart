.. _cheatsheet:

Cheatsheet
==========

Basic App
---------

.. code-block:: python

    from quart import Quart

    app = Quart(__name__)

    @app.route("/hello")
    async def hello():
        return "Hello, World!"

    if __name__ == "__main__":
        app.run(debug=True)

Routing
-------

.. code-block:: python

    @app.route("/hello/<string:name>")  # example.com/hello/quart
    async def hello(name):
        return f"Hello, {name}!"

Request Methods
---------------

.. code-block:: python

    @app.route("/get")  # GET Only by default
    @app.route("/get", methods=["GET", "POST"])  # GET and POST
    @app.route("/get", methods=["DELETE"])  # Just DELETE

JSON Responses
--------------

.. code-block:: python

    @app.route("/hello")
    async def hello():
        return {"Hello": "World!"}

Template Rendering
------------------

.. code-block:: python

    from quart import render_template

    @app.route("/hello")
    async def hello():
        return await render_template("index.html")  # Required to be in templates/

Configuration
-------------

.. code-block:: python

    import json
    import toml

    app.config["VALUE"] = "something"

    app.config.from_file("filename.toml", toml.load)
    app.config.from_file("filename.json", json.load)

Request
-------

.. code-block:: python

    from quart import request

    @app.route("/hello")
    async def hello():
        request.method
        request.url
        request.headers["X-Bob"]
        request.args.get("a")  # Query string e.g. example.com/hello?a=2
        await request.get_data()  # Full raw body
        (await request.form)["name"]
        (await request.get_json())["key"]
        request.cookies.get("name")

WebSocket
---------

.. code-block:: python

    from quart import websocket

    @app.websocket("/ws")
    async def ws():
        websocket.headers
        while True:
            try:
                data = await websocket.receive()
                await websocket.send(f"Echo {data}")
            except asyncio.CancelledError:
                # Handle disconnect
                raise

Cookies
-------

.. code-block:: python

    from quart import make_response

    @app.route("/hello")
    async def hello():
        response = await make_response("Hello")
        response.set_cookie("name", "value")
        return response

Abort
-----

.. code-block:: python

    from quart import abort

    @app.route("/hello")
    async def hello():
        abort(409)


HTTP/2 & HTTP/3 Server Push
---------------------------

.. code-block:: python

    from quart import make_push_promise, url_for

    @app.route("/hello")
    async def hello():
        await make_push_promise(url_for('static', filename='css/minimal.css'))
        ...
