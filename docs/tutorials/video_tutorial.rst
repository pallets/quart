.. _video_tutorial:

Tutorial: Serving video
=======================

In this tutorial we will build a very basic video server. It will
serve a video directly.

This tutorial is meant to serve as an introduction to serving large
files with conditional responses in Quart. If you want to skip to the
end the code is on `Github
<https://github.com/pgjones/quart/example/video>`_.

1: Creating the project
-----------------------

We need to create a project for our video server, I like to use
`Poetry <https://python-poetry.org>`_ to do this. Poetry is installed
via pip (or via `Brew <https://brew.sh/>`_):

.. code-block:: console

    pip install poetry

We can then use Poetry to create a new video project:

.. code-block:: console

    poetry new --src video

Our project can now be developed in the *video* directory, and all
subsequent commands should be in run the *video* directory.

2: Adding the dependencies
--------------------------

We only need Quart to build this simple video server, which we can
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
following addition to *src/video/__init__.py*:

.. code-block:: python
    :caption: src/video/__init__.py

    from quart import Quart

    app = Quart(__name__)

    def run() -> None:
        app.run()

To make the app easy to run we can call the run method from a poetry
script, by adding the following to *pyproject.toml*:

.. code-block:: toml
    :caption: pyproject.toml

    [tool.poetry.scripts]
    start = "video:run"

Which allows the following command to start the app:

.. code-block:: console

    poetry run start

4: Serving the UI
-----------------

When users visit our website we will show them the same video served
directly, and via chunks. The following HTML template should be added
to *src/video/templates/index.html*:

.. code-block:: html
    :caption: src/video/templates/index.html

    <video controls width="100%">
      <source src="/video.mp4" type="video/mp4">
    </video>

This is a very basic UI in terms of the styling.

We can now serve this template for the root path i.e. ``/`` by adding
the following to *src/video/__init__.py*:

.. code-block:: python

    from quart import render_template

    @app.get("/")
    async def index():
        return await render_template("index.html")

5: Implementing the routes
--------------------------

As we are serving a large file we should allow for conditional
responses. This is where the data returned in the response is
conditional on what the request asked for. This is done via the
``Range`` header field which can be inspected via the
``request.range`` attribute.

Quart has in-built methods to make a response conditional on the
request range. The first is to use the conditional argument when
sending a file, the second is to use the response ``make_conditional``
method. The former is shown below, which should be added to
*src/video/__init__.py*:

.. code-block:: python
    :caption: src/video/__init__.py

    @app.route("/video.mp4")
    async def auto_video():
        return await send_file("video.mp4", conditional=True)

6: Testing
----------

To test our app we need to check that the full video is returned
unless a conditional range request is made. This is done by adding the
following to *tests/test_video.py*:

.. code-block:: python
    :caption: tests/test_video.py

    from video import app

    async def test_auto_video() -> None:
        test_client = app.test_client()
        response = await test_client.get("/video.mp4")
        data = await response.get_data()
        assert len(data) == 255_849

        response = await test_client.get("/video.mp4", headers={"Range": "bytes=200-1000"})
        data = await response.get_data()
        assert len(data) == 801

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

We've built a server that will serve large files conditionally as
requested by the client, including the ability to limit the maximum
partial size.
