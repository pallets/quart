.. _http2_discussion:

HTTP/2
======

Quart is based on the excellent `hyper-h2
<https://github.com/python-hyper/hyper-h2>`_ library.

TLS settings
------------

The recommendations in this documentation for the SSL/TLS ciphers and
version are from `RFC 7540 <https://tools.ietf.org/html/rfc7540>`_. As
required in the RFC ``ECDHE+AESGCM`` is the minimal cipher set HTTP/2
and TLSv2 the minimal TLS version servers should support.

ALPN Protocol
~~~~~~~~~~~~~

The ALPN Protocols should be set to include ``h2`` and ``http/1.1`` as
Quart supports both. It is feasible to omit one to only serve the
other. If these aren't set most clients will assume Quart is a
HTTP/1.1 only server.

No-TLS
~~~~~~

Most clients, including all the web browsers only support HTTP/2 over
TLS. Quart, however, supports the h2c HTTP/1.1 to HTTP/2 upgrade
process. This allows a client to send a HTTP/1.1 request with a
``Upgrade: h2c`` header that results in the connection being upgraded
to HTTP/2. To test this try

.. code-block::

   $ curl --http2 http://url:port/path

Note that in the absence of either the upgrade header or an ALPN
protocol Quart will assume and treat the connection as HTTP/1.1.

HTTP/2 features
---------------

Quart supports pipeling, flow control, and server push, it doesn't (as
yet) support prioritisation.
