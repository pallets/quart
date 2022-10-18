.. _installation:

Installation
============

Quart is only compatible with Python 3.7 or higher and can be installed
using pip or your favorite python package manager:

.. code-block:: console

    pip install quart

If you do not have Python 3.7 or better an error message ``Python 3.7
is the minimum required version`` will be displayed.

Dependencies
------------

Quart dependends on the following packages, which will automatically
be installed with Quart:

- aiofiles, to load files in an asyncio compatible manner,
- blinker, to manager signals,
- click, to manage command line arguments
- hypercorn, an ASGI server for development,
- importlib_metadata only for Python 3.7,
- itsdangerous, for signing secure cookies,
- jinja2, for template rendering,
- markupsafe, for markup rendering,
- typing_extensions only for Python 3.7,
- werkzeug, as the basis of many Quart classes.

You can choose to install with the dotenv extra:

.. code-block:: console

    pip install quart[dotenv]

Whcih will install the ``python-dotenv`` package which enables support
for automatically loading environment variables when running ``quart``
commands.

See also
--------

`Poetry <https://python-poetry.org>`_ for project management.
