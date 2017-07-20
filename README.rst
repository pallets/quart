Quart
=====

|Build Status| |docs|

Quart is a Python asyncio web microframework with the same API as
`Flask <https://github.com/pallets/flask>`_. Quart should provide a
very minimal step to use `Asyncio
<https://docs.python.org/3/library/asyncio.html>`_ in a Flask app.

Quickstart
----------

Quart can be installed via `pip
<https://docs.python.org/3/installing/index.html>`_ ``pip install
quart`` and requires Python 3.6+. A minimal Quart example would be

.. code-block:: python

    from quart import Quart

    app = Quart(__name__)

    @app.route('/')
    async def hello():
        return 'hello'

    app.run()

if the above is in a file called ``app.py`` can be run via ``python
app.py``. To deploy in a production setting see the `docs
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

.. |docs| image:: https://readthedocs.org/projects/docs/badge/?version=latest
   :target: https://pgjones.gitlab.io/quart/
