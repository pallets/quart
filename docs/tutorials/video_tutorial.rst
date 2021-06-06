.. video_tutorial:

Tutorial: Video
===============

This tutorial will guide you through building the video server present
in the ``examples/video`` directory. This is a very simple app that
responds conditionally to the requests i.e. it will allow the HTML
video tag to work correctly.

Running the example
'''''''''''''''''''

To run the example, in ``examples/video`` the following should start
the server, (see :ref:`installation` first),

.. code-block:: console

    $ export QUART_APP=video:app
    $ quart run

the video is then available at `http://localhost:5000/
<http://localhost:5000/>`_. Note you will need to place a video file
called ``video.mp4`` alongside the ``video.py`` file for this to work.

1: Structure
------------

Quart by default expects the code to be structured in a certain way in
order for templates and static file to be found. This means that you
should structure the video app as follows,

::

    video/
    video/templates/
    video/video.mp4

doing so will also make your project familiar to others, as you follow
the same convention.

2: Installation
---------------

It is always best to run python projects with a pipenv, which
should be created and activated as follows,

.. code-block:: console

    $ cd video
    $ pipenv install quart

for this video we will only need Quart. Now pipenv can be activated,

.. code-block:: console

    $ pipenv shell

3: Conditional Responses
------------------------

Conditional responses allow the server to send only the data that the
client has requested. The client indicates this by attaching a
``Range`` header to the request, which can be retrieved manually via,

.. code-block:: python

    range = request.range
    range.units  # Usually bytes
    range.ranges  # List of requests ranges

as hinted this is quite common for videos, given the large size.

A server doesn't have to respond conditionally, and can in fact always
send the entire file. As it is optional you have to choose to use it,
via the :meth:`~quart.wrappers.response.Response.make_conditional`
method. Like so,

.. code-block:: python

    response = await send_file(...)  # Or any response
    await response.make_conditional(request.range)

as a client you can tell the difference via the status code, 200 is
the full response and 206 a partial response.

4: Conclusion
-------------

The example files contain this entire tutorial and a little more, so
they are now worth a read. Hopefully you can now go ahead and create
and serve videos or any other file conditionally.
