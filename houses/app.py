from flask import Flask, g
from flask_wtf.csrf import CsrfProtect
from flask.ext.bcrypt import Bcrypt
from flask.ext.login import LoginManager
from flask.ext.bootstrap import Bootstrap


app = Flask(__name__)


SECRET_KEY = 'really_secret'
WTF_CSRF_SECRET_KEY = 'really_secret_too'


app.config.from_object(__name__)
login_manager = LoginManager()
login_manager.init_app(app)


CsrfProtect(app)
bcrypt = Bcrypt(app)
Bootstrap(app)


@login_manager.user_loader
def load_user(id):
    return User.get(id=id)

from .models import BaseModel, database, UserNotAvailableError
# This hook ensures that a connection is opened to handle any queries
# generated by the request.
@app.before_request
def _db_connect():
    database.connect()

# This hook ensures that the connection is closed when we've finished
# processing the request.
@app.teardown_request
def _db_close(exc):
    if not database.is_closed():
        database.close()


@app.before_first_request
def setup_database():
    for cls in BaseModel.tables():
        #  cls.drop_table(fail_silently=True)
        cls.create_table(fail_silently=True)
    try:
        User.get_or_create(username="Ben", password="degeleis2jaaroud")
        User.get_or_create(username="Melissa", password="degeleis2jaaroud")
    except UserNotAvailableError:
        pass


from .controllers import *
