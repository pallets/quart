.. _http2_discussion:

HTTP/2
======

Quart is based on the excellent `hyper-h2
<https://github.com/python-hyper/hyper-h2>`_ library

TLS settings
------------

The recommendations in this documentation for the SSL/TLS ciphers and
version are from `RFC 7540 <https://tools.ietf.org/html/rfc7540>`_. As
required in the RFC ``ECDHE+AESGCM`` is the minimal cipher set HTTP/2
and TLSv2 the minimal TLS version servers should support.

HTTP/2 features
---------------

Quart supports pipeling, flow control, and server push it doesn't (as
yet) support prioritisation.
