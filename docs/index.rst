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

Quart is developed on `GitLab <https://gitlab.com/pgjones/quart>`_.
You are very welcome to open `issues
<https://gitlab.com/pgjones/quart/issues>`_ or propose `merge requests
<https://gitlab.com/pgjones/quart/merge_requests>`_.

Tutorials
---------

.. toctree::
   :maxdepth: 1

   installation.rst
   quickstart.rst
   AsyncProgressBar_tutorial.rst
   blog_tutorial.rst
   broadcast_tutorial.rst
   flask_ext_tutorial.rst
   http2_tutorial.rst
   websocket_tutorial.rst
   deployment.rst
   large_application.rst
   asyncio.rst

How-To Guides
-------------

.. toctree::
   :maxdepth: 1

   background_tasks.rst
   blueprints.rst
   command_line.rst
   configuration.rst
   factory_pattern.rst
   flask_extensions.rst
   flask_migration.rst
   json_encoding.rst
   logging.rst
   request_body.rst
   routing.rst
   session_storage.rst
   streaming_response.rst
   templating.rst
   testing.rst
   using_http2.rst
   websockets.rst

Discussion Points
-----------------

.. toctree::
   :maxdepth: 1

   async_compatibility.rst
   contexts.rst
   design_choices.rst
   dos_mitigations.rst
   flask_evolution.rst
   globals.rst
   timeout.rst
   websockets_discussion.rst

Reference
---------

.. toctree::
   :maxdepth: 1

   api.rst
   logo.rst
   response_values.rst
