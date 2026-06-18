"""
Django settings for CONEVENT / SIGEA project.
"""

from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-zm_j!+%^3+_(thmqaaqlwuy43^plkdv-z26uwel(8f19xma6xn'

DEBUG = True

ALLOWED_HOSTS = []

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
    'corsheaders',                       # <-- CORS Headers
    'reportes',                          # <-- Reportes y analíticas
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
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
    ),
}

# ─── Configuración de Simple JWT ─────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),  # Expiración cómoda para desarrollo
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ─── Configuración de CORS ───────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True  # Permitir cualquier origen en desarrollo
CORS_ALLOW_CREDENTIALS = True