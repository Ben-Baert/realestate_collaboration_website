from realestate import app, login_manager
from .models import database, User


@app.before_request
def _db_connect():
    database.connect()


@app.teardown_request
def _db_close(exc):
    if not database.is_closed():
        database.close()


@login_manager.user_loader
def load_user(_id):
    return User.get(_id=_id)
