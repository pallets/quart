from quart import Blueprint

main = Blueprint('main', __name__, template_folder = 'templates', static_folder = 'static',static_url_path='/main')

from .routes import *
