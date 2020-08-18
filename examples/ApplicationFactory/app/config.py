from pathlib import Path
path = Path().absolute()

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///'+str(path)+'/Database/database.db'
SECRET_KEY = 'e9515dfe457bfe64c1c30d73e161de0f76f6b03f'

