import quart.flask_patch

from secrets import compare_digest

from quart import Quart, redirect, request, url_for
import flask_login

app = Quart(__name__)
app.secret_key = 'secret'  # Create an actual secret key for production
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# Rather than storing passwords in plaintext, use something like
# bcrypt or similar to store the password hash.
users = {'quart': {'password': 'secret'}}


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
    from flask import render_template_string
    username = request.form.get('username')
    password = request.form.get('password', '')
    if username not in users:
        return

    user = User()
    user.id = username
    user.is_authenticated = compare_digest(password, users[username]['password'])
    return user


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


@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized'


if __name__ == '__main__':
    app.run()
