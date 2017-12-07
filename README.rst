Quart
=====

.. image:: https://assets.gitlab-static.net/pgjones/quart/raw/master/artwork/logo.png
   :alt: Quart logo


|Build Status| |docs| |pypi| |http|

Quart is a Python asyncio web microframework with the same API as
`Flask <https://github.com/pallets/flask>`_. Quart should provide a
very minimal step to use `Asyncio
<https://docs.python.org/3/library/asyncio.html>`_ in a Flask app.
See the `docs <https://pgjones.gitlab.io/quart/>`_.

Quart extends the Flask-API by adding support for

- HTTP/1.1, including chunked transfer-encoded requests and
  pipelining.
- Websockets.
- HTTP/2, including the ability to server push.


Quickstart
----------

Quart can be installed via `pip
<https://docs.python.org/3/installing/index.html>`_ ``pip install quart``
and requires Python 3.6+. A minimal Quart example would be

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

if the above is in a file called ``app.py`` can be run via ``python app.py``.
To deploy in a production setting see the `docs
<https://pgjones.gitlab.io/quart/deployment.html>`_.

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
