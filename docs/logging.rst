.. _logging:

Logging
=======

The standard Python logging machinery can be safely used with
Quart. Additionally Quart provides a pre configured logger that
standardises the format and log level (based on the app
configuration).

To use the Quart logger simply use the :attr:`~quart.app.Quart.logger`
as you would a standard Python logger (it is a standard Python
logger), e.g.

.. code-block:: python

    app.logger.warning("Easy now")
    app.logger.info("Interesting")

Output Format
-------------

The Quart Logger outputs in the formats defined in
:attr:`~quart.logging.PRODUCTION_LOG_FORMAT` and
:attr:`~quart.logging.DEBUG_LOG_FORMAT`.
