.. _large_application:

Building a large application
============================

Following on from the quickstart app with the assumption that the
number of routes and amount of code present has made a the single
module unmanageable. A likely first solution is to simply split the
code into modules and import the app from the initial module in each,
perhaps like,

**main.py**

.. code-block:: python

    from quart import Quart

    app = Quart(__name__)
    ...
    import extra

**extra.py**

.. code-block:: python

    from main import app

    @app.route('/extra/')
    def extra():
        ...

however this quickly leads to circular imports and other problems. The
solution is to use a blueprint for the extra module, like so,

**main.py**

.. code-block:: python

    from quart import Quart

    from extra import blueprint

    app = Quart(__name__)
    app.register_blueprint(blueprint)
    ...

**extra.py**

.. code-block:: python

    from quart import Blueprint

    blueprint = Blueprint('extra', __name__)

    @blueprint.route('/extra/')
    def extra():
        ...
