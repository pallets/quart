.. _blueprints:

Blueprints
==========

Blueprints allow for modular code, they should be used whenever the
routes start to span multiple modules. Blueprints, like the app can have
template and static files, therefore a typical folder structure for a
blueprint termed ``store`` would be,

.. code-block::

    blueprints/
    blueprints/store/__init__.py
    blueprints/store/templates/
    blueprints/store/templates/index.html
    blueprints/store/static/

the ``__init__.py`` file should contain something like,

.. code-block:: python

    from quart import Blueprint

    blueprint = Blueprint(__name__)

    @blueprint.route('/')
    def index():
        return render_template('index.html')
