.. flask_ext_tutorial:

Tutorial: Using a Flask Extension
=================================

This tutorial will guide you through using a Flask extension with
Quart. The code for this tutorial is present in the
``examples/flask_ext`` directory. The example itself is a very simple
webpage that allows a user to login, check a protected route and
logout.

Running the example
'''''''''''''''''''

To run the example, in ``examples/flask_ext`` the following should
start the server, (see :ref:`installation` first),

.. code-block:: console

    $ export QUART_APP=flask_ext:app
    $ quart run

this example is then available at `http://localhost:5000/
<http://localhost:5000/>`_.

1: Installation
---------------

It is always best to run python projects within a pipenv, which
should be created and activated as follows, (Python 3.6 or better is
required),

.. code-block:: console

    $ cd flask_ext
    $ pipenv install quart flask-login

for this we will only need Quart and Flask-Login. Now pipenv can
be activated,

.. code-block:: console

    $ pipenv shell

3: Using Flask-Login with Quart
-------------------------------

`Flask-Login <https://flask-login.readthedocs.io>`_ is a very popular
Flask extension that manages user authentication. To use it with Quart
it is important to first activate the flask patching module in Quart,
by the following,

.. code-block:: python

    import quart.flask_patch

as this allows the extensions to find modules and objects in the flask
namespace.

.. warning::

   This import must be the first line in your code, i.e. it must be in
   the main or init module at the top. This line comes with a
   performance cost.

The Flask-Login extension can now be used, as so,

.. code-block:: python
    :caption: flask_ext.py

    import quart.flask_patch

    import flask_login
    from quart import Quart

    app = Quart(__name__)
    app.secret_key = 'secret'  # Create an actual secret key for production
    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)

4: Flask-Login setup
--------------------

Flask-Login requires the following code be present to manage the
users, notably to load a User given a request, to load a user given
their username and to return a message for unauthorized access,

.. code-block:: python
    :caption: flask_ext.py

    from secrets import compare_digest

    from quart import request

    class User(flask_login.UserMixin):
        pass

    @login_manager.user_loader
    def user_loader(username):
        if username not in users:
            return

        user = User()
        user.id = username
        return user

    @login_manager.request_loader
    def request_loader(request):
        username = request.form.get('username')
        password = request.form.get('password', '')
        if username not in users:
            return

        user = User()
        user.id = username
        user.is_authenticated = compare_digest(password, users[username]['password'])
        return user

    @login_manager.unauthorized_handler
    def unauthorized_handler():
        return 'Unauthorized'

5: Routes
---------

All that is left is to provide login, logout and a protected route to
test that the app works. A user can then try to access the protected
route when not authorised and then after login. These routes are,

.. code-block:: python
    :caption: flask_ext.py

    from quart import redirect, url_for

    @app.route('/', methods=['GET', 'POST'])
    async def login():
        if request.method == 'GET':
            return '''
                   <form method='POST'>
                    <input type='text' name='username' id='username' placeholder='username'></input>
                    <input type='password' name='password' id='password' placeholder='password'></input>
                    <input type='submit' name='submit'></input>
                   </form>
                   '''

        username = (await request.form)['username']
        password = (await request.form)['password']
        if username in users and compare_digest(password, users[username]['password']):
            user = User()
            user.id = username
            flask_login.login_user(user)
            return redirect(url_for('protected'))

        return 'Bad login'


    @app.route('/protected')
    @flask_login.login_required
    async def protected():
        return 'Logged in as: ' + flask_login.current_user.id


    @app.route('/logout')
    async def logout():
        flask_login.logout_user()
        return 'Logged out'

6: Conclusion
-------------

The example files contain this entire tutorial and a little more, so
they are now worth a read. Hopefully you can now go ahead and create
your own apps that use Flask extensions.
