:orphan:

.. title:: Quart documentation

.. image:: _static/logo.png
   :width: 300px
   :alt: Quart logo

Quart is a Python web microframework based on Asyncio. It is intended
to provide the easiest way to use asyncio in a web context, especially
with exiting Flask apps. If you are new to Python you should start by
reading :ref:`installation`, if you are new to Quart then see
:ref:`quickstart` and if you are also new to Asyncio see
:ref:`asyncio`. If however you are very familiar with Flask, see
:ref:`flask_migration`.

Quart is an evolution of the `Flask <http://flask.pocoo.org/>`_ API to
work with Asyncio and to provide a number of features not present or
possible in Flask, see :ref:`flask_evolution`. Compatibility with the
Flask API is however the main aim, which means that the `Flask
documentation <http://flask.pocoo.org/docs/>`_ is an additional useful
source of help.

Tutorials
---------

.. toctree::
   :maxdepth: 1

   installation.rst
   quickstart.rst
   deployment.rst
   large_application.rst
   asyncio.rst

How-To Guides
-------------

.. toctree::
   :maxdepth: 1

   blueprints.rst
   command_line.rst
   configuration.rst
   factory_pattern.rst
   flask_extensions.rst
   flask_migration.rst
   serving_http2.rst
   json_encoding.rst
   logging.rst
   request_body.rst
   session_storage.rst
   templating.rst
   testing.rst
   websockets.rst

Discussion Points
-----------------

.. toctree::
   :maxdepth: 1

   async_compatibility.rst
   contexts.rst
   design_choices.rst
   flask_evolution.rst
   globals.rst
   http2_discussion.rst
   timeout.rst

Reference
---------

.. toctree::
   :maxdepth: 1

   api.rst
   logo.rst
   response_values.rst
