.. _blog_tutorial:

Tutorial: Building a simple blog
================================

In this tutorial we will build a simple blog with entries stored in a
database. We'll then render these posts on the server and serve the
HTML directly to the user.

This tutorial is meant to serve as an introduction to building server
rendered websites in Quart. If you want to skip to the end the code is
on `Github <https://github.com/pallets/quart/tree/main/examples/blog>`_.

1: Creating the project
-----------------------

We need to create a project for our blog server, I like to use
`Poetry <https://python-poetry.org>`_ to do this. Poetry is installed
via pip (or via `Brew <https://brew.sh/>`_):

.. code-block:: console

    pip install poetry

We can then use Poetry to create a new blog project:

.. code-block:: console

    poetry new --src blog

Our project can now be developed in the *blog* directory, and all
subsequent commands should be in run the *blog* directory.

2: Adding the dependencies
--------------------------

To start we only need Quart to build the blog server, which we can
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
following addition to *src/blog/__init__.py*:

.. code-block:: python
    :caption: src/blog/__init__.py

    from quart import Quart

    app = Quart(__name__)

    def run() -> None:
        app.run()

To make the app easy to run we can call the run method from a poetry
script, by adding the following to *pyproject.toml*:

.. code-block:: toml
    :caption: pyproject.toml

    [tool.poetry.scripts]
    start = "blog:run"

Which allows the following command to start the app:

.. code-block:: console

    poetry run start

4: Creating the database
------------------------

There are many database management systems to choose from depending
upon the needs and requirements. In this case we need only the
simplest system, and Python’s standard library includes SQLite making
it the easiest.

To initialise the database we need the following SQL to create the
correct table, as added to *src/blog/schema.sql*:

.. code-block:: sql
    :caption: src/blog/schema.sql

    DROP TABLE IF EXISTS post;
    CREATE TABLE post (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      'text' TEXT NOT NULL
    );

Next we need to be able to create the database on command, which
we can do by adding the command code to *src/blog/__init__.py*:

.. code-block:: python
    :caption: src/blog/__init__.py

    from pathlib import Path
    from sqlite3 import dbapi2 as sqlite3

    app.config.update({
      "DATABASE": Path(app.root_path) / "blog.db",
    })

    def _connect_db():
        engine = sqlite3.connect(app.config["DATABASE"])
        engine.row_factory = sqlite3.Row
        return engine

    def init_db():
        db = _connect_db()
        with open(Path(app.root_path) / "schema.sql", mode="r") as file_:
            db.cursor().executescript(file_.read())
        db.commit()

Next we need to update the poetry scripts in *pyproject.toml* to be:

.. code-block:: toml
    :caption: pyproject.toml

    [tool.poetry.scripts]
    init_db = "blog:init_db"
    start = "blog:run"

Now we can run the following to create and update the database:

.. code-block:: console

    poetry run init_db

.. warning::

   Running this command will wipe any existing data.


5: Displaying posts in the database
-----------------------------------

With can now display the posts present in the database. To do so we
first need a template to render the posts as HTML. This is as follows
and should be added to *src/blog/templates/posts.html*:

.. code-block:: html
    :caption: src/blog/templates/posts.html

    <main>
      {% for post in posts %}
        <article>
          <h2>{{ post.title }}</h2>
          <p>{{ post.text|safe }}</p>
        </article>
      {% else %}
        <p>No posts available</p>
      {% endfor %}
    </main>

Now we need a route to query the database, retrieve the messages,
and render the template. As done with the following code which should
be added to *src/blog/__init__.py*:

.. code-block:: python
    :caption: src/blog/__init__.py

    from quart import render_template, g

    def _get_db():
        if not hasattr(g, "sqlite_db"):
            g.sqlite_db = _connect_db()
        return g.sqlite_db

    @app.get("/")
    async def posts():
        db = _get_db()
        cur = db.execute(
            """SELECT title, text
                 FROM post
             ORDER BY id DESC""",
        )
        posts = cur.fetchall()
        return await render_template("posts.html", posts=posts)

6: Creating a new post
----------------------

To create blog posts we first need a form into which a user can enter
the post details. This is done via the following template code that should
be added to *src/blog/templates/create.html*:

.. code-block:: html
    :caption: src/blog/templates/create.html

    <form method="POST" style="display: flex; flex-direction: column; gap: 8px; max-width:400px">
      <label>Title: <input type="text" size="30" name="title" /></label>
      <label>Text: <textarea name="text" rows="5" cols="40"></textarea></label>
      <button type="submit">Create</button>
    </form>

The styling ensures that the elements of the form are arranged
verically with a gap and sensible maximum width.

To allow a visitor to create a blog post we need to accept the POST
request generated by this form in the browser. To do so the following
should be added to *src/blog/__init__.py*:

.. code-block:: python
    :caption: src/blog/__init__.py

    from quart import redirect, request, url_for

    @app.route("/create/", methods=["GET", "POST"])
    async def create():
        if request.method == "POST":
            db = _get_db()
            form = await request.form
            db.execute(
                "INSERT INTO post (title, text) VALUES (?, ?)",
                [form["title"], form["text"]],
            )
            db.commit()
            return redirect(url_for("posts"))
        else:
            return await render_template("create.html")

This route handler will render the creation form in response to a GET
request e.g. via navigation in the browser. However, for a POST
request it will extract the form data to create a blog post before
redirecting the user to the page with the posts.

7: Testing
----------

To test our app we need to check that a blog post can be created, and
once done so shows on the posts page. Firstly we need to create a
temporary database for testing, which we can do using a pytest fixture
placed in *tests/conftest.py*:

.. code-block:: python
    :caption: tests/conftest.py

    import pytest

    from blog import app, init_db

    @pytest.fixture(autouse=True)
    def configure_db(tmpdir):
        app.config['DATABASE'] = str(tmpdir.join('blog.db'))
        init_db()

This fixture will run automatically before our tests, thereby setting up
a database we can use in the tests.

To test the creation and display we can add the following to
*tests/test_blog.py*:

.. code-block:: python
    :caption: tests/test_blog.py

    from blog import app

    async def test_create_post():
        test_client = app.test_client()
        response = await test_client.post("/create/", form={"title": "Post", "text": "Text"})
        assert response.status_code == 302
        response = await test_client.get("/")
        text = await response.get_data()
        assert b"<h2>Post</h2>" in text
        assert b"<p>Text</p>" in text

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

We've built a simple database backed blog server. This should be a
good starting point to building any type of server rendered app.
