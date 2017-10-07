.. _timeout:

Timeouts
========

Quart has only a concept of an idle connection timeout, which is
roughly the same as a keep alive timeout. Unlike other implementations
e.g. Nginx this does not allow asymetric i.e. different timeouts
before, during and after a request is handled.

This roughly matches the use case of Flask with Gunicorn, whereby the
keep alive timeout takes affect, but with most workers there is no
pre-request (idle connection) timeout.
