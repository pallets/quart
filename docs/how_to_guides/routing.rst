.. _routing:

Routing
=======

Quart allows for multiple and complex routes to be defined, allowing a
client to trigger specific code depending on the method and path
requested.

The simplest routing is simple static rules, such as the following,

.. code-block:: python

    @app.route('/')
    async def index():
        ...

    @app.route('/about')
    async def about():
        ...

which is often sufficient for mostly static websites.

Dynamic routing
---------------

Dynamic routing can be achieved by using ``<variable>`` markers which
specify that part of the route can be matched rather than
pre-defined. For example,

.. code-block:: python

    @app.route('/page/<page_no>')
    async def page(page_no):
        ...

will match paths ``/page/1``, ``/page/2``, and ``/page/jeff`` with the
``page_no`` argument set to ``'1'``, ``'2'``, and ``'jeff'``
respectively.

Converters
~~~~~~~~~~

It is often necessary and useful to specify how the variable should
convert and by implication match paths. This works by adding the
converter name before the variable name separated by a colon,
``<converter:variable>``. Adapting the example above to,

.. code-block:: python

    @app.route('/page/<int:page_no>')
    async def page(page_no):
        ...

will match paths ``/page/1``, and ``/page/2`` with the ``page_no``
argument set to ``1``, and ``2`` (note types) but will no longer match
``/page/jeff`` as ``jeff`` cannot be converted to an int.

The available converters are,

========== ==========================================
``float``  positive floating point numbers
``int``    positive integers
``path``   like ``string`` with slashes
``string`` (default) any text without a slash
``uuid``   UUID strings
========== ==========================================

note that additional converters can be added to the
:attr:`~quart.app.Quart.url_map` :attr:`~quart.routing.Map.converters`
dictionary.

Default values
--------------

Variable usage can sometimes prove annoying to users, for example
``/page/<int:page_no>`` will not match ``/page`` forcing the user to
specify ``/page/1``. This can be solved by specifying a default value,

.. code-block:: python

    @app.route('/page', defaults={'page_no': 1})
    @app.route('/page/<int:page_no>')
    async def page(page_no):
        ...

which allows ``/page`` to match with ``page_no`` set to ``1``.


Host matching, host and subdomain
---------------------------------

Routes can be added to the app with an explicit ``host`` or
``subdomain`` to match if the app has host matching enabled. This
results in the routes only matching if the host header matches, for
example ``host='quart.com'`` will allow the route to match any request
with a host header of ``quart.com`` and otherwise 404.

The ``subdomain`` option can only be used if the app config
``SERVER_NAME`` is set, as the host will be built up as
``{subdomain}.{SERVER_NAME}``.

Note that the variable converters can be used in the host or subdomain
options.
