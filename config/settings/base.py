from pathlib import Path
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Security — Admin URL prefix (UUID, never /admin/ in production)
# ---------------------------------------------------------------------------
ADMIN_URL_PREFIX = 'a3f8c1e7-9b42-4d6a-b5e0-7f2a1c3d8e9b'
CMS_URL_PREFIX = 'b7d2e4f6-8a13-4c59-9e71-0d3b5a7f9c1e'

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Whitenoise runserver must be first in INSTALLED_APPS for functionality in dev
    'whitenoise.runserver_nostatic',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 3rd Party
    'django_cotton',
    'django_htmx',
    'tailwind',
    
    # Local
    'theme',
    'home',
    'courses',
    'contact',
    'registration',
    'cms',
    'marketing',
]

# ──────────────────────────────────────────────
# Email configuration
# ──────────────────────────────────────────────

EMAIL_ADDRESSES = {
    'contact': 'contact@institut-torii.com',
    'inscription': 'inscription@institut-torii.com',
    'notification': 'notification@institut-torii.com',
}

DEFAULT_FROM_EMAIL = 'Institut Torii <contact@institut-torii.com>'

# Batch settings for campaign sending
EMAIL_BATCH_SIZE = 50
EMAIL_BATCH_DELAY = 2  # seconds between batches

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Whitenoise 2nd
    'whitenoise.middleware.WhiteNoiseMiddleware',
    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # HTMX Middleware
    'django_htmx.middleware.HtmxMiddleware',

    # Analytics (after Session + Auth so request.session/user are available)
    'cms.middleware.AnalyticsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'fr'

TIME_ZONE = 'Africa/Algiers'

USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('fr', _('Français')),
    ('en', _('English')),
    ('ar', _('العربية')),
    ('ja', _('日本語')),
    ('zh-hans', _('中文')),
    ('ko', _('한국어')),
]

LOCALE_PATHS = [BASE_DIR / 'locale']


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Allow file uploads up to 10 MB (payment receipts can be large PDFs)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Tailwind
TAILWIND_APP_NAME = 'theme'
TAILWIND_USE_STANDALONE_BINARY = True
