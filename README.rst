Quart
=====

.. image:: https://assets.gitlab-static.net/pgjones/quart/raw/master/artwork/logo.png
   :alt: Quart logo

|Build Status| |docs| |pypi| |http| |python| |license| |chat|

Quart is a Python `ASGI
<https://github.com/django/asgiref/blob/master/specs/asgi.rst>`_ web
microframework. It is intended to provide the easiest way to use
asyncio functionality in a web context, especially with existing Flask
apps. This is possible as the Quart API is a superset of the `Flask
<https://github.com/pallets/flask>`_ API.

Quart aims to be a complete web microframework, as it supports
HTTP/1.1, HTTP/2 and websockets. Quart is very extendable and has a
number of known `extensions
<https://pgjones.gitlab.io/quart/quart_extensions.html>`_ and works
with many of the `Flask extensions
<https://pgjones.gitlab.io/quart/flask_extensions.html>`_.

Quickstart
----------

Quart can be installed via `pipenv
<https://docs.pipenv.org/install/#installing-packages-for-your-project>`_ or
`pip <https://docs.python.org/3/installing/index.html>`_,

.. code-block:: console

    $ pipenv install quart
    $ pip install quart

and requires Python 3.7.0 or higher (see `python version support
<https://pgjones.gitlab.io/quart/python_versions.html>`_ for
reasoning).

A minimal Quart example is,

.. code-block:: python

    from quart import Quart, websocket

    app = Quart(__name__)

    @app.route('/')
    async def hello():
        return 'hello'

    @app.websocket('/ws')
    async def ws():
        while True:
            await websocket.send('hello')

    app.run()

if the above is in a file called ``app.py`` it can be run as,

.. code-block:: console

    $ python app.py

To deploy in a production setting see the `deployment
<https://pgjones.gitlab.io/quart/deployment.html>`_ documentation.

Features
--------

Quart supports the full ASGI 3.0 specification as well as the
websocket response and HTTP/2 server push extensions. For those of you
familiar with Flask, Quart extends the Flask-API by adding support for,

- HTTP/1.1 request streaming.
- Websockets.
- HTTP/2 server push.

Note that not all ASGI servers support these features, for this reason
the recommended server is `Hypercorn
<https://gitlab.com/pgjones/hypercorn>`_.

Contributing
------------

Quart is developed on `GitLab <https://gitlab.com/pgjones/quart>`_. If
you come across an issue, or have a feature request please open an
`issue <https://gitlab.com/pgjones/quart/issues>`_.  If you want to
contribute a fix or the feature-implementation please do (typo fixes
welcome), by proposing a `merge request
<https://gitlab.com/pgjones/quart/merge_requests>`_.

Testing
~~~~~~~

The best way to test Quart is with `Tox
<https://tox.readthedocs.io>`_,

.. code-block:: console

    $ pipenv install tox
    $ tox

this will check the code style and run the tests.

Help
----

The Quart `documentation <https://pgjones.gitlab.io/quart/>`_ is the
best place to start, after that try searching `stack overflow
<https://stackoverflow.com/questions/tagged/quart>`_, if you still
can't find an answer please `open an issue
<https://gitlab.com/pgjones/quart/issues>`_.

API Compatibility with Flask
----------------------------

The Flask API can be described as consisting of the Flask public and
private APIs and Werkzeug upon which Flask is based. Quart is designed
to be fully compatible with the Flask public API (aside from async and
await keywords). Thereafter the aim is to be mostly compatible with
the Flask private API and to provide no guarantees about the Werkzeug
API.

Migrating from Flask
~~~~~~~~~~~~~~~~~~~~

It should be possible to migrate to Quart from Flask by a find and
replace of ``flask`` to ``quart`` and then adding ``async`` and
``await`` keywords. See the `docs
<https://pgjones.gitlab.io/quart/flask_migration.html>`_ for full
details.


.. |Build Status| image:: https://gitlab.com/pgjones/quart/badges/master/build.svg
   :target: https://gitlab.com/pgjones/quart/commits/master

.. |docs| image:: https://img.shields.io/badge/docs-passing-brightgreen.svg
   :target: https://pgjones.gitlab.io/quart/

.. |pypi| image:: https://img.shields.io/pypi/v/quart.svg
   :target: https://pypi.python.org/pypi/Quart/

.. |http| image:: https://img.shields.io/badge/http-1.0,1.1,2-orange.svg
   :target: https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol

.. |python| image:: https://img.shields.io/pypi/pyversions/quart.svg
   :target: https://pypi.python.org/pypi/Quart/

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://gitlab.com/pgjones/quart/blob/master/LICENSE

.. |chat| image:: https://img.shields.io/badge/chat-join_now-brightgreen.svg
   :target: https://gitter.im/python-quart/lobby
