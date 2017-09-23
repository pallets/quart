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
