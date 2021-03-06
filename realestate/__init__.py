from flask import Flask
from flask_wtf.csrf import CsrfProtect
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_mail import Mail, Message
from flask_googlemaps import GoogleMaps
from flask_pagedown import PageDown
from flaskext.markdown import Markdown
from .utils import ListConverter


app = Flask(__name__)
app.config.from_object('config')

app.url_map.converters['list'] = ListConverter

login_manager = LoginManager()
login_manager.init_app(app)

csrf = CsrfProtect(app)

bcrypt = Bcrypt(app)

Bootstrap(app)

mail = Mail(app)

GoogleMaps(app)

pagedown = PageDown(app)

Markdown(app)

from .hooks import *
from .controllers import *
from .filters import *
from .celery import *
from .setup import *
