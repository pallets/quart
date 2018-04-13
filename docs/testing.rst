.. _testing:

Testing
=======

Quart's usage of global variables (``request`` etc) makes testing any
code that uses these variables more difficult. To combat this it is
best practice to only use these variables in the code directly called
by Quart e.g. route functions or before request functions. Thereafter
Quart provides a testing framework to control these globals.

Primarily testing should be done using a test client bound to the
Quart app being tested. As this is so common there is a helper method
:meth:`~quart.app.Quart.test_client` which returns a bound client,
e.g.

.. code-block:: python

    @pytest.mark.asyncio
    async def test_app(app):
        client = app.test_client()
        response = await client.get('/')
        assert response.status_code == 200

Event loops
-----------

To test with quart you will need to have an event loop in order to
call the async functions. This is possible to do manually, for example

.. code-block:: python

    def aiotest(func):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(func())

    @aiotest
    async def test_app(app)
        ...

However it is much easier to use ``pytest-asyncio`` and the
``@pytest.mark.asyncio`` decorator to do this for you. Note that
``pytest`` is the recommended test runner and the examples throughout
assume ``pytest`` is used with ``pytest-asyncio``.

Calling routes
--------------

The test client has helper methods for all the HTTP verbs
e.g. :meth:`~quart.testing.QuartClient.post`. These are helper methods
for :meth:`~quart.testing.QuartClient.open`, as such all the methods at
a minimum expect a path and optionally can have query parameters, json
or form data. A standard :class:`~quart.wrappers.Response` class is
returned. An example:

.. code-block:: python

    @pytest.mark.asyncio
    async def test_create(app):
        test_client = app.test_client()
        data = {'name': 'foo'}
        response = await test_client.post('/resource/', json=data)
        assert response.status_code == 201
        result = await response.get_json()
        assert result == data

Context testing
---------------

It is often necessary to test something within the app or request
context_. This is simple enough for the app context,

.. code-block:: python

    @pytest.mark.asyncio
    async def test_app_context(app):
        async with app.app_context():
            current_app.[use]

for the request context however the request context has to be faked,
at a minimum this means the method and path must be supplied, e.g.

.. code-block:: python

    @pytest.mark.asyncio
    async def test_app_context(app):
        async with app.test_request_context('GET', '/'):
            request.[use]
