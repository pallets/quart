.. _how_to_log:

Logging
=======

Quart has a standard Python logger sharing the same name as the
``app.name``. To use it, simply make use of
:attr:`~quart.app.Quart.logger`, for example:

.. code-block:: python

    app.logger.info('Interesting')
    app.logger.warning('Easy Now')

Configuration
-------------

The Quart logger is not created until its first usage, which may occur
as the app is created. These loggers on creation respect any existing
configuration. This allows the loggers to be configured like any other
python logger, for example

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

The handler :attr:`~quart.logging.default_handler` attached to the
quart logger can be removed like so,

.. code-block:: python

    from logging import getLogger
    from quart.logging import default_handler

    getLogger(app.name).removeHandler(default_handler)
