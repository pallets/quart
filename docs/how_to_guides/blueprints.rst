.. _blueprints:

Blueprints
==========

Blueprints allow for modular code, they should be used whenever the
routes start to span multiple modules. Blueprints, like the app can have
template and static files, therefore a typical folder structure for a
blueprint termed ``store`` would be,

::

    blueprints/
    blueprints/store/__init__.py
    blueprints/store/templates/
    blueprints/store/templates/index.html
    blueprints/store/static/

the ``__init__.py`` file should contain something like,

.. code-block:: python

    from quart import Blueprint

    blueprint = Blueprint('store', __name__)

    @blueprint.route('/')
    def index():
        return render_template('index.html')


the endpoint is then identified as ``store.index`` for example when
using ``url_for('store.index')``.

Nested Blueprints
-----------------

It is possible to register a blueprint on another blueprint.

.. code-block:: python

    parent = Blueprint("parent", __name__, url_prefix="/parent")
    child = Blueprint("child", __name__, url_prefix="/child)
    parent.register_blueprint(child)
    app.register_blueprint(parent)

The child blueprint will gain the parent's name as a prefix to its
name, and child URLs will be prefixed with the parent's URL prefix.

.. code-block:: python

    url_for('parent.child.create')
    /parent/child/create

Blueprint-specific before request functions, etc. registered with the
parent will trigger for the child. If a child does not have an error
handler that can handle a given exception, the parent's will be tried.
