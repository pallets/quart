.. blog_tutorial:

Tutorial: A simple blog
=======================

This tutorial will guide you through building the blog present in the
``examples/blog`` directory. This is a very simple blog that displays
a list of posts and allows an authenticated user to create a new post.

Running the example
'''''''''''''''''''

To run the example, in ``examples/blog`` the following should start
the server, (see :ref:`installation` first),

.. code-block:: console

    $ export QUART_APP=blog:app
    $ quart run

the blog is then available at `http://localhost:5000/
<http://localhost:5000/>`_.

1: Structure
------------

Quart by default expects the code to be structured in a certain way in
order for templates and static file to be found. This means that you
should structure the blog as follows,

::

    blog/
    blog/static/
    blog/static/js/
    blog/static/css/
    blog/templates/

doing so will also make your project familiar to others, as you follow
the same convention.

2: Installation
---------------

It is always best to run python projects within a pipenv, which
should be created and activated as follows, (Python 3.6 or better is
required),

.. code-block:: console

    $ cd blog
    $ pipenv install quart

for this blog we will only need Quart. Now pipenv can be activated,

.. code-block:: console

    $ pipenv shell

.. Note::

   ``(venv)`` is used to indicate when the commands must be run within
   the pipenv's virtualenv.

3: Creating the app
-------------------

We can now create a basic hello world app, in a file called
``blog.py``,

.. code-block:: python
   :caption: blog.py

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def index():
        return 'Hello World'

and run it by the following,

.. code-block:: console

    $ export QUART_APP=blog:app
    (venv) $ quart run

.. note::

   The ``QUART_APP`` environment variable is assumed to be set for the
   rest of this tutorial.

4: Creating the database
------------------------

There are many database management systems to choose from depending
upon the needs and requirements. In this case we need only the
simplest system, and Python's standard library includes SQLite making
it the easiest.

To initialise the database we need some SQL to create the correct
table,

.. code-block:: sql
   :caption: schema.sql

    DROP TABLE IF EXISTS post;
    CREATE TABLE post (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      'text' TEXT NOT NULL
    );

which ensures that the post table exists in this form. This is a
command that will need to be used often, so it should be a cli
command. This is achieved via the following ``blog.py`` additions,

.. code-block:: python
   :caption: blog.py

    from sqlite3 import dbapi2 as sqlite3

    app.config.update({
      'DATABASE': os.path.join(app.root_path, 'blog.db'),
    })

    def connect_db():
        engine = sqlite3.connect(app.config['DATABASE'])
        engine.row_factory = sqlite3.Row
        return engine

    @app.cli.command()
    def init_db():
        """Create an empty database."""
        db = connect_db()
        with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), mode='r') as file_:
            db.cursor().executescript(file_.read())
        db.commit()

which allows,

.. code-block:: console

    (venv) $ quart init_db

to run the init_db function, creating a blank database.

.. warning::

   Running the schema or the command will wipe any existing data.

5: Displaying posts in the database
-----------------------------------

With the database existing we can display the posts present in it. To
do so we have to query the database and retreive the messages, this is
best done in the view-function, with the following code (which replaces
the existing ``/`` view-function in ``blog.py``),

.. code-block:: python
   :caption: blog.py

    from quart import render_template

    def get_db():
        if not hasattr(g, 'sqlite_db'):
            g.sqlite_db = connect_db()
        return g.sqlite_db

    @app.route('/', methods=['GET'])
    async def posts():
        db = get_db()
        cur = db.execute(
            """SELECT title, text
                 FROM post
             ORDER BY id DESC""",
        )
        posts = cur.fetchall()
        return await render_template('posts.html', posts=posts)

This ``posts`` view-function returns the awaited result of a template
render, which displays the posts. This template should exist within
the ``templates`` directory and contain the following,

.. code-block:: html
   :caption: templates/posts.html

     <div class="posts">
      {% for post in posts %}
        <div><h2>{{ post.title }}</h2>{{ post.text|safe }}</div>
      {% else %}
        <div>No posts available</div>
      {% endfor %}
     </div>

in order to nicely render HTML displaying the posts.

6: Creating a new post
----------------------

To allow a visitor to create a blog-post we should accept a POST
request from the browser. This POST request should contian all the
information we need to create a blog-post, namely the title and
text. With this the blog-post can be created with the following
view-function addition to ``blog.py``,

.. code-block:: python
   :caption: blog.py

    from quart import redirect, request, url_for

    @app.route('/', methods=['POST'])
    async def create():
        db = get_db()
        form = await request.form
        db.execute(
            "INSERT INTO post (title, text) VALUES (?, ?)",
            [form['title'], form['text']],
        )
        db.commit()
        return redirect(url_for('posts'))

the redirect sends the POST request browser to the ``posts``
view-function.

You can test this using curl with the following command,

.. code-block:: console

    $ curl -X POST -d "title=Blog Title&text=Text for the blog" localhost:5000/

This is not very helpful to most visitors though, instead we should
use a HTML form. This can be added to the ``posts.html`` template as so,

.. code-block:: html
   :caption: templates/posts.html

    <form action="{{ url_for('create') }}" method="post" class="create-post">
      <p>Title:<input type="text" size="30" name="title">
      <p>Text:<textarea name="text" rows="5" cols="40"></textarea>
      <p><input type="submit" value="Post">
      </dl>
    </form>

with the action pointing at out new ``create`` view-function.

7: Authenticating visitors
--------------------------

So far we can view and create posts, but so can anyone visiting the
site. Ideally we should restrict the ability to create posts to a
subset of visitors, notably visitors we allow. Therefore we need to
authenticated visitors.

An authenticated visitor is typically different to the other visitors
in that they present some proof of authentication. Initially this must
be their username and password. Thereafter a market on the cookie is
set to indicate they are logged in. With Quart the
:ref:`session_storage` is secure by default, so it can be used as so,

.. code-block:: python

    from quart import session

    @app.route('/login')
    def login():
        session['logged_in'] = True
        ...

    @app.route('/posts')
    def posts():
        if session['logged_in']:
            # Do something authenticated
        else:
            # Do something else
        ...

    @app.route('/logout')
    def logout():
        session.pop('logged_in', None)

we can also check in the templates if the user is logged in,

.. code-block:: jinja

    <nav>
      {% if not session.logged_in %}
        <a href="{{ url_for('login') }}">Login</a>
      {% else %}
        <a href="{{ url_for('logout') }}">Logout</a>
      {% endif %}
    </nav>

.. note::

   In production you probably want a more sophisticated authentication
   system, of which `Flask-Login
   <https://flask-login.readthedocs.io/en/latest/>`_ is the best
   example.

8: All together
---------------

Now that visitors can be authenticated the app needs to offer login
and logout view functions alongside checking the the authentication
status when creating posts. This combined is,

.. code-block:: python
   :caption: blog.py

    from quart import (
        abort, redirect, render_template, request, session,
        url_for,
    )

    app.config.update({
        'SECRET_KEY': 'development key',
        'USERNAME': 'admin',
        'PASSWORD': 'default',
    })

    @app.route('/', methods=['POST'])
    async def create():
        if not session.get('logged_in'):
            abort(401)
        db = get_db()
        form = await request.form
        db.execute(
            "INSERT INTO post (title, text) VALUES (?, ?)",
            [form['title'], form['text']],
        )
        db.commit()
        return redirect(url_for('posts'))

    @app.route('/login/', methods=['GET', 'POST'])
    async def login():
        error = None
        if request.method == 'POST':
            form = await request.form
            if form['username'] != app.config['USERNAME']:
                error = 'Invalid username'
            elif form['password'] != app.config['PASSWORD']:
                error = 'Invalid password'
            else:
                session['logged_in'] = True
                return redirect(url_for('posts'))
        return await render_template('login.html', error=error)

    @app.route('/logout/')
    async def logout():
        session.pop('logged_in', None)
        await flash('You were logged out')
        return redirect(url_for('posts'))

.. warning::

   In production don't store the passwords in plain text, rather use
   something like bcrypt (salting and hashing).

The login template itself is given as below,

.. code-block:: html
   :caption: templates/login.html

    <h2>Login</h2>
    {% if error %}<p class="error"><strong>Error:</strong> {{ error }}{% endif %}
    <form action="{{ url_for('login') }}" method="post">
      <p>Username: <input type="text" name="username">
      <p>Password: <input type="password" name="password">
      <p><input type="submit" value="Login">
    </form>

9: Flashing messages
--------------------

So far every action the visitor completes is silently completed,
however we should give the visitor some feedback. This is where
flashing messages proves very helpful. For example after login it
makes sense to flash if the login was successful, like so,

.. code-block:: python

    await flash('You were logged in')

which requires the following jinja addition to every template,

.. code-block:: jinja

    {% for message in get_flashed_messages() %}
      <div class="flash">{{ message }}</div>
    {% endfor %}

To avoid repeating ourselves and adding this snippet to every single
template, we can instead create a base template and have the other
templates inherit from it. We could also have used a template macro,
but the base template helps with the styling in the next section. The
base template should be,

.. code-block:: jinja
   :caption: templates/base.html

    <!doctype html>
    <title>Blog</title>
    <h1><a href="{{ url_for('posts') }}">Blog</a></h1>
    {% for message in get_flashed_messages() %}
      <div class="flash">{{ message }}</div>
    {% endfor %}
    <div class="content">
      {% block content %}
      {% endblock %}
    </div>

The other templates can then use this base template via the following construct,

.. code-block:: jinja

    {% extends 'base.html' %}
    {% block content %}
      ...
    {% endblock %}

10: Styling
-----------

The pages can be styled using css, firstly by adding this one line to
the base template,

.. code-block:: html
   :caption: templates/base.html

    <link rel="stylesheet" type="text/css" href="{{ url_for('static', filename='blog.css') }}">

and then by adding this stylesheet to ``static/blog.css``,

.. code-block:: css
   :caption: static/blog.css

    body {
      background: #f5f5f6;
      font-family: sans-serif;
      margin: 0;
      padding: 0;
    }

    h1 {
      background: #004c40;
      padding: 0.2em;
    }

    ...

see the full example for more.

11: Testing
-----------

You should be testing your apps, and Quart provides testing clients
and functionality to make this easy. Using the `pytest
<https://docs.pytest.org/>`_ test framework rather than the stdlib
unittest framework makes things easier still, and will be used
here. pytest and pytest-asyncio (as required to test asyncio code) can
be installed using pipenv,

.. code-block:: console

    (venv) $ pipenv install pytest pytest-asyncio

A useful test would be to check that posts are created as expected,
which means we need to test against the database. Fortunately pytest
offers a tmpdir fixture which is perfect for this, so lets create a
test app fixture,

.. code-block:: python

    import pytest

    from .blog import app, init_db


    @pytest.fixture(name='test_app')
    def _test_app(tmpdir):
        app.config['DATABASE'] = str(tmpdir.join('blog.db'))
        init_db()
        return app

which we can use in any test function by expecting an argument named
``test_app``.

The test itself should be to POST a new blog-post to the create route
and then check it exists in the list of posts,

.. code-block:: python

    @pytest.mark.asyncio
    async def test_create(test_app):
        test_client = test_app.test_client()
        await test_client.post(
            '/login/',
            form={
                'username': test_app.config['USERNAME'],
                'password': test_app.config['PASSWORD']
            },
        )
        response = await test_client.post(
            '/', form={'title': 'test_title', 'text': 'test_text'},
        )
        assert response.status_code == 301
        response = await test_client.get('/')
        body = await response.get_data(raw=False)
        assert 'test_title' in body
        assert 'test_text' in body

which is testable via,

.. code-block:: console

    (venv) $ pytest

12: Conclusion
--------------

The example files contain this entire tutorial and a little more, so
they are now worth a read. Hopefully you can now go ahead and create
your own apps.
