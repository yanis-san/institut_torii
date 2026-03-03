from .base import *

DEBUG = True

SECRET_KEY = 'django-insecure-dev-key'

ALLOWED_HOSTS = []

INSTALLED_APPS += ['django_browser_reload']

MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")


INTERNAL_IPS = [
    "127.0.0.1",
]

# Email — console backend for dev (prints emails to terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
