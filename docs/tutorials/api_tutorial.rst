.. _api_tutorial:

Tutorial: Building a RESTful API
================================

In this tutorial we will build a RESTful JSON API. It will
automatically generate OpenAPI documentation and validate request and
response data.

This tutorial is meant to serve as an introduction to building APIs in
Quart. If you want to skip to the end the code is on `Github
<https://github.com/pgjones/quart/example/api>`_.

1: Creating the project
-----------------------

We need to create a project for our api server, I like to use
`Poetry <https://python-poetry.org>`_ to do this. Poetry is installed
via pip (or via `Brew <https://brew.sh/>`_):

.. code-block:: console

    pip install poetry

We can then use Poetry to create a new api project:

.. code-block:: console

    poetry new --src api

Our project can now be developed in the *api* directory, and all
subsequent commands should be in run the *api* directory.

2: Adding the dependencies
--------------------------

To start we only need Quart to build the api server, which we can
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
following addition to *src/api/__init__.py*:

.. code-block:: python
    :caption: src/api/__init__.py

    from quart import Quart

    app = Quart(__name__)

    def run() -> None:
        app.run()

To make the app easy to run we can call the run method from a poetry
script, by adding the following to *pyproject.toml*:

.. code-block:: toml
    :caption: pyproject.toml

    [tool.poetry.scripts]
    start = "api:run"

Which allows the following command to start the app:

.. code-block:: console

    poetry run start

4: Adding simple JSON API
-------------------------

To start we can add a route that reads the JSON sent to it and echos
it back in a response by adding the following to
*src/api/__init__.py*:

.. code-block:: python
    :caption: src/api/__init__.py

    from quart import request

    @app.post("/echo")
    async def echo():
        data = await request.get_json()
        return {"input": data, "extra": True}

We can test this using curl:

.. code-block:: console

    curl --json '{"hello": "world"}' http://localhost:5000/echo

Which gives the following result:

.. code-block:: console

    {"extra":true,"input":{"hello":"world"}}

To be explicit any dictionary returned from a route handler will be
returned in the response as JSON with the correct Content-Type
header. If you want to return a top level array as the JSON response
the ``jsonify`` function can be used as so:

.. code-block:: python

    from quart import jsonify

    @app.get("/example")
    async def example():
        return jsonify(["a", "b"])

5: Adding schemas
-----------------

Using the `Quart-Schema <https://github.com/pgjones/quart-schema>`_
extension we can define schemas to validate the request and response
data. In addition Quart-Schema will then utilise these schemas to
auto-generate OpenAPI (Swagger) documentation. To start we need to
install quart-schema:

.. code-block:: console

    poetry add quart-schema

We can then add schemas for a Todo object by adding the following to
*src/api/__init__.py*:

.. code-block:: python
    :caption: src/api/__init__.py

    from dataclasses import dataclass
    from datetime import datetime

    from quart_schema import QuartSchema, validate_request, validate_response

    QuartSchema(app)

    @dataclass
    class TodoIn:
        task: str
        due: datetime | None

    @dataclass
    class Todo(TodoIn):
        id: int

    @app.post("/todos/")
    @validate_request(TodoIn)
    @validate_response(Todo)
    async def create_todo(data: Todo) -> Todo:
        return Todo(id=1, task=data.task, due=data.due)

The OpenAPI schema is then available at
http://localhost:5000/openapi.json and the docs themselves at
http://localhost:5000/docs.

6: Testing
----------

To test our app we need to check that the echo route returns the JSON
data sent to it and the create_todo route creates a todo. This is done
by adding the following to *tests/test_api.py*:

.. code-block:: python
    :caption: tests/test_api.py

    from api import app, TodoIn

    async def test_echo() -> None:
        test_client = app.test_client()
        response = await test_client.post("/echo", json={"a": "b"})
        data = await response.get_json()
        assert data == {"extra":True,"input":{"a":"b"}}

    async def test_create_todo() -> None:
        test_client = app.test_client()
        response = await test_client.post("/todos/", json=TodoIn(task="Abc", due=None))
        data = await response.get_json()
        assert data == {"id": 1, "task": "Abc", "due": None}

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

7: Summary
----------

We've built a RESTful API server with autogenerated OpenAPI docs and
validation. You can now take this code and build any API.
