"""
Django settings for CONEVENT / SIGEA project.
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-zm_j!+%^3+_(thmqaaqlwuy43^plkdv-z26uwel(8f19xma6xn')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ─── APPS ────────────────────────────────────────────────────
# IMPORTANTE: 'usuarios' debe ir ANTES de 'django.contrib.admin'
# para que Django registre el modelo de usuario personalizado correctamente
INSTALLED_APPS = [
    'usuarios',                          # <-- PRIMERO la app con AUTH_USER_MODEL
    'espacios',                          # <-- App de gestión de espacios / stands
    'inventario',                        # <-- App de gestión de inventario / QR
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',                    # <-- Django REST Framework
    'rest_framework_simplejwt.token_blacklist', # <-- JWT Blacklist
    'corsheaders',                       # <-- CORS Headers
    'reportes',                          # <-- Reportes y analíticas
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',       # <-- Whitenoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',            # <-- CORS middleware (debe ir antes de CommonMiddleware)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conevent.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'conevent.wsgi.application'

DATABASES = {
    'default': config('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3', cast=dj_database_url.parse)
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internacionalización ────────────────────────────────────
LANGUAGE_CODE = 'es-mx'           # <-- Cambiado a español México
TIME_ZONE = 'America/Mexico_City' # <-- Zona horaria correcta para UTEQ
USE_I18N = True
USE_TZ = True

# ─── Archivos estáticos ──────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Modelo de usuario personalizado ────────────────────────
AUTH_USER_MODEL = 'usuarios.Usuario'  # REQUERIDO para que funcione todo

# ─── Redirecciones de login ──────────────────────────────────
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'

# Correos en consola durante desarrollo
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ─── Backends de autenticación ──────────────────────────────
# Permite login con username O correo institucional
AUTHENTICATION_BACKENDS = [
    'usuarios.backends.EmailOrUsernameBackend',  # Nuestro backend personalizado
    'django.contrib.auth.backends.ModelBackend', # Respaldo nativo de Django
]

# ─── Configuración de Django REST Framework (DRF) ────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}

# ─── Configuración de Simple JWT ─────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ─── Configuración de CORS ───────────────────────────────────
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://127.0.0.1:3000', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# ─── Configuración de Sesiones ────────────────────────────────
SESSION_COOKIE_AGE = 86400

# ─── Configuración de Correo SMTP ─────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@conevent.com')

# ─── Archivos de Media ────────────────────────────────────────
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR

# ─── Headers de Seguridad HTTP ────────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
