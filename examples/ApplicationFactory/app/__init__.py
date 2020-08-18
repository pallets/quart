from quart import Quart, flask_patch
from app.main import main
from .extinsions import db

def create_app():
    app = Quart(__name__)
    app.config.from_pyfile('config.py')
    db.init_app(app)
	
    app.register_blueprint(main)

    return app

