.. _how_to_log:

Logging
=======

By default Quart has two loggers, named ``quart.app`` and
``quart.serving``, both are standar Python Loggers. The former is
usually kept for app logging whilst the latter serving. To use the
former, simply make use of :attr:`~quart.app.Quart.logger`, for
example:

.. code-block:: python

    app.logger.info('Interesting')
    app.logger.warning('Easy Now')

The serving logger is typically reserved for the serving code, but can
be used if required via :func:`logging.getLogger` i.e.
``getLogger('quart.serving')``.

Configuration
-------------

The Quart loggers are not created until their first usage, which may
occur as the app is created. These loggers on creation respect any
existing configuration. This allows the loggers to be configured like
any other python logger, for example

.. code-block:: python

    from logging.config import dictConfig

    dictConfig({
        'version': 1,
        'loggers': {
            'quart.app': {
                'level': 'ERROR',
            },
        },
    })

Disabling/removing handlers
---------------------------

The handlers attached to the quart loggers can be removed, the
handlers are :attr:`~quart.logging.default_handler` and
:attr:`~quart.logging.default_serving_handler` and can be removed like
so,

.. code-block:: python

    from logging import getLogger
    from quart.logging import default_handler

    getLogger('quart.app').removeHandler(default_handler)

Configuring access logs
-----------------------

The access log format can be configured by specifying the atoms (see
below) to include in a specific format. By default quart will choose
``%(h)s %(r)s %(s)s %(b)s %(D)s`` as the format.

The default Flask (Werkzeug) access log format is ``%(h)s - - %(t)s
"%(r)s" %(s)s %(b)s``. Which should be combined with a
:attr:`~quart.logging.default_serving_handler` that only formats a
message,

.. code-block:: python

    from logging import Formatter
    from quart.logging import serving_handler

    serving_handler.setFormatter(Formatter('%(message)s'))


Access log atoms
````````````````

The following atoms, as matches `Gunicorn
<https://github.com/benoitc/gunicorn>`_, are available for use.

===========  ===========
Identifier   Description
===========  ===========
h            remote address
l            ``'-'``
u            user name
t            date of the request
r            status line (e.g. ``GET / h11``)
m            request method
U            URL path without query string
q            query string
H            protocol
s            status
B            response length
b            response length or ``'-'`` (CLF format)
f            referer
a            user agent
T            request time in seconds
D            request time in microseconds
L            request time in decimal seconds
p            process ID
{Header}i    request header
{Header}o    response header
{Variable}e  environment variable
===========  ===========
