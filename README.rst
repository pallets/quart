Quart
=====

.. image:: https://assets.gitlab-static.net/pgjones/quart/raw/master/artwork/logo.png
   :alt: Quart logo

|Build Status| |docs| |pypi| |http| |python| |license|

Quart is a Python web microframework based on `Asyncio
<https://docs.python.org/3/library/asyncio.html>`_. It is intended to
provide the easiest way to use the asyncio functionality in a web
context, especially with existing Flask apps. This is possible as Quart
has the same API as `Flask <https://github.com/pallets/flask>`_.

Quart aims to be a complete web microframework, as it supports
HTTP/1.1, HTTP/2 and websockets. Quart also aims to be very extendable
and works with many of the `Flask extensions
<https://pgjones.gitlab.io/quart/flask_extensions.html>`_, (hopefully
Quart specific extensions will be written soon).

Quickstart
----------

Quart can be installed via `pip
<https://docs.python.org/3/installing/index.html>`_,

.. code-block:: console

    $ pip install quart

and requires Python 3.6 or higher.

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

Quart has all the features required to serve webpages over HTTP. For
those of you familar with Flask, Quart extends the Flask-API by adding
support for,

- HTTP/1.1 chunked transfer-encoded requests and pipelining.
- Websockets.
- HTTP/2, including the ability to server push.

Contributing
------------

Quart is developed on `GitLab
<https://gitlab.com/pgjones/quart>`_. You are very welcome to open
`issues <https://gitlab.com/pgjones/quart/issues>`_ or propose `merge
requests <https://gitlab.com/pgjones/quart/merge_requests>`_.

Testing
~~~~~~~

Tox is best used test Quart,

.. code-block:: console

    $ pip install tox
    $ tox

this will check the code style and run the tests.

Help
----

The Quart `documentation <https://pgjones.gitlab.io/quart/>`_ is the
best place to start, after that try opening an `issue
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
