.. http2_tutorial:

Tutorial: Using HTTP/2
======================

This tutorial will guide you through serving HTTP/2 and making use of
HTTP/2's server push. The code for this tutorial is present in the
``examples/http2`` directory. The example itself is a very simple
webpage that does calculation on a server (it isn't really practical).

Running the example
'''''''''''''''''''

To run the example, in ``examples/http2`` the following should start
the server, (see :ref:`installation` first),

.. code-block:: console

    $ export QUART_APP=http2:app
    $ quart run

this example is then available at `https://localhost:5000/
<https://localhost:5000/>`_.

1: Structure
------------

Quart by default expects the code to be structured in a certain way in
order for templates and static file to be found. This means that you
should structure the blog as follows,

::

    http2/
    http2/static/
    http2/static/js/
    http2/static/css/
    http2/templates/

doing so will also make your project familiar to others, as you follow
the same convention.

2: Installation
---------------

It is always best to run python projects within a pipenv, which
should be created and activated as follows, (Python 3.6 or better is
required),

.. code-block:: console

    $ cd http2
    $ pipenv install quart

for this we will only need Quart. Now pipenv can be activated,

.. code-block:: console

    $ pipenv shell

.. Note::

   ``(venv)`` is used to indicate when the commands must be run within
   the pipenv's virtualenv.

3: Creating the app
-------------------

We can now create a basic hello world app, in a file called
``http2.py``. This app has to be served over HTTPS in order for a
browser to use HTTP/2, this requires SSL certificates to be provided
and that the default ``quart run`` command is overridden with one that
adds SSL. To create the certificates run and accept the defaults,

.. code-block:: console

    $ openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

.. warning::

   You shouldn't use these certificates in production, see :ref:`ssl`
   for details.

The command itself and app code is then, see :ref:`http2` for the full
details on the SSL settings,

.. code-block:: python
    :caption: http2.py

    import ssl

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def index():
        return 'Hello World'

    @app.cli.command('run')
    def run():
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
        ssl_context.set_ciphers('ECDHE+AESGCM')
        ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
        ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
        app.run(port=5000, ssl=ssl_context)

and run it by the following,

.. code-block:: console

    $ export QUART_APP=blog:app
    (venv) $ quart run

The hello world is then available at `https://localhost:5000/
<https://localhost:5000/>`_ and should be served using the ``h2``
protocol (see the developer toolbar in the browser).

.. note::

   The ``QUART_APP`` environment variable is assumed to be set for the
   rest of this tutorial.

4: Using server push
--------------------

Server push allows for the server to send responses to the client
before the client sends the request. This is useful when the server
can predict what the client will request, thereby saving time at the
possible cost of bandwidth if the prediction is wrong.

In this example we will return html that references a css and a js
file, and hence we can predict that the client will request both
files. This allows us to push the files to the client before the
client requests it.

To do so we simply change the index view-function to,

.. code-block:: python
    :caption: http2.py

    from quart import make_response, render_template, url_for

    @app.route('/')
    async def index():
        response = await make_response(await render_template('index.html'))
        response.push_promises.add(url_for('static', filename='http2.css'))
        response.push_promises.add(url_for('static', filename='http2.js'))
        return response

5: Calculation
--------------

In addition to using HTTP/2 we actually want to do some calculation on
the server and return the result to the client. The calculation is
simple, accept JSON containing two values ``a`` and ``b`` and a
``operator``, perform the operation and then return the result as
JSON,

.. code-block:: python
    :caption: http2.py

    from quart import abort, jsonify, request

    @app.route('/', methods=['POST'])
    async def calculate():
        data = await request.get_json()
        operator = data['operator']
        try:
            a = int(data['a'])
            b = int(data['b'])
        except ValueError:
            abort(400)
        if operator == '+':
            return jsonify(a + b)
        elif operator == '-':
            return jsonify(a - b)
        elif operator == '*':
            return jsonify(a * b)
        elif operator == '/':
            return jsonify(a / b)
        else:
            abort(400)

The client side requires the following HTML elements, two inputs ``a``
and ``b`` and the various operations,

.. code-block:: html
    :caption: templates/index.html

    <body>
      <p>
        <input type="number" name="a" placeholder="a">
        <input type="number" name="b" placeholder="b">
        <label id="result">?</span>
      </p>
      <p>
        <button id="add">Add a and b</button>
        <button id="subtract">Subtract b from a</button>
        <button id="multiply">Multiply a and b</button>
        <button id="divide">Divide a by b</button>
      </p>
    </body>

and the following javascript to send the POST request and deal with
the response,

.. code-block:: javascript
    :caption: static/http2.js

    document.addEventListener('DOMContentLoaded', function() {
      var calculate = function(operator) {
        fetch('/', {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify ({
            a: document.getElementsByName("a")[0].value,
            b: document.getElementsByName("b")[0].value,
            operator: operator
          }),
        }).then(
            function(response) {return response.json()
        .then(
          function(data) {document.getElementById('result').innerText = data;
        }).catch(function() {});
      };
      document.getElementById('add').onclick = function(event) {calculate('+'); return false;};
      document.getElementById('subtract').onclick = function(event) {calculate('-'); return false;};
      document.getElementById('multiply').onclick = function(event) {calculate('*'); return false;};
      document.getElementById('divide').onclick = function(event) {calculate('/'); return false;};
    });

6: Conclusion
-------------

The example files contain this entire tutorial and a little more, so
they are now worth a read. Hopefully you can now go ahead and create
your own apps that are served over http/2.
