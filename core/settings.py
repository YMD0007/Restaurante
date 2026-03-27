"""
Django settings for core project.
Configurado para despliegue en Render 🚀
"""

import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key
import dj_database_url

# ==============================
# 📁 BASE
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================
# 🔐 SEGURIDAD
# ==============================
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or get_random_secret_key()

# En Render DEBUG = False automáticamente
DEBUG = 'RENDER' not in os.environ

ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Para desarrollo local
if DEBUG:
    ALLOWED_HOSTS += ['localhost', '127.0.0.1']


# ==============================
# 📦 APLICACIONES
# ==============================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Tu app
    'gestion',
]


# ==============================
# ⚙️ MIDDLEWARE
# ==============================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    # 🔥 CLAVE para Render
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ==============================
# 🌐 URLS / TEMPLATES
# ==============================
ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'gestion.context_processors.puntos_usuario',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# ==============================
# 🗄️ BASE DE DATOS
# ==============================
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=not DEBUG
    )
}


# ==============================
# 🔑 PASSWORDS
# ==============================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
]


# ==============================
# 🌍 INTERNACIONALIZACIÓN
# ==============================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ==============================
# 📁 STATIC FILES
# ==============================
STATIC_URL = 'static/'

if not DEBUG:
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ==============================
# 📁 MEDIA FILES
# ==============================
MEDIA_URL = '/media/'

CUSTOM_MEDIA_ROOT = os.environ.get('MEDIA_ROOT', '').strip()
RENDER_DISK_PATH = os.environ.get('RENDER_DISK_PATH', '').strip()

if CUSTOM_MEDIA_ROOT:
    MEDIA_ROOT = CUSTOM_MEDIA_ROOT
elif RENDER_DISK_PATH:
    MEDIA_ROOT = os.path.join(RENDER_DISK_PATH, 'media')
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

os.makedirs(MEDIA_ROOT, exist_ok=True)


# ==============================
# 🔐 LOGIN
# ==============================
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'
LOGIN_URL = '/login/'


# ==============================
# 📧 EMAIL
# ==============================
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in {'true', '1', 'yes'}

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@example.com')


# ==============================
# 🔢 PRIMARY KEY
# ==============================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'