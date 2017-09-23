.. _logging:

Logging
=======

The standard Python logging machinery can be safely used with
Quart. Additionally Quart provides a pre configured logger that
standardises the format and log level under the ``quart`` logger
namespace.

To use the Quart logger simply use the :attr:`~quart.app.Quart.logger`
as you would a standard Python logger (it is a standard Python
logger), and is named ``quart.app``, e.g.

.. code-block:: python

    app.logger.warning("Easy now")
    app.logger.info("Interesting")

The Quart ``quart.app`` logger is created and configured on first
usage (potentially during app creation), so it is best to `pre
configure
<https://docs.python.org/3/howto/logging-cookbook.html#logging-cookbook>`_
the logging for your app before creating an instance of
:class:`~quart.app.Quart`. Note that by default (unless the app debug
is True) this logger will not have a set logging level.

The default handler used in the ``quart.app`` logger is
:attr:`~quart.logging.default_handler` and can be removed via

.. code-block:: python

    from quart.logging import default_handler
    app.logger.removeHandler(default_handler)

Output Format
-------------

The Quart Logger outputs in ``[%(asctime)s] %(levelname)s in
%(module)s: %(message)s`` format as defined in
:mod:`~quart.logging`.
