import os

REALESTATE_ROOT = os.environ.get('realestateroot', '.')
SECRET_KEY = 'really_secret_t'
WTF_CSRF_SECRET_KEY = 'really_secret_too'
MAIL_SERVER = 'smtp.googlemail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
#MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
#MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = 'flask@example.com'
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None) 
CELERY_REDIS_PASSWORD = REDIS_PASSWORD
CELERY_BROKER_URL = "redis://:{REDIS_PASSWORD}@localhost:{REDIS_PORT}/0".format(REDIS_PASSWORD=REDIS_PASSWORD, REDIS_PORT=REDIS_PORT)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL 
