from pathlib import Path
import os


# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SEGURANÇA
# ============================================================

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-this"
)

DEBUG = (
    os.environ.get(
        "DEBUG",
        "True"
    ).lower()
    == "true"
)


# ============================================================
# HOSTS
# ============================================================

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost"
    ).split(",")
    if host.strip()
]


# ============================================================
# APLICAÇÕES
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Aplicações do projeto
    "inicio",
    "produtos",
    "categorias",
    "diagnostico",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URLS
# ============================================================

ROOT_URLCONF = "config.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# WSGI
# ============================================================

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# BANCO DE DADOS
# ============================================================

DATABASE_URL = os.environ.get("DATABASE_URL")


if DATABASE_URL:

    try:
        import dj_database_url

        DATABASES = {
            "default": dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=600,
                ssl_require=True,
            )
        }

    except ImportError:

        raise ImportError(
            "O pacote 'dj-database-url' é necessário "
            "quando DATABASE_URL está configurada."
        )

else:

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ============================================================
# VALIDAÇÃO DE PASSWORD
# ============================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME":
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator",
    },
]


# ============================================================
# INTERNACIONALIZAÇÃO
# ============================================================

LANGUAGE_CODE = "pt-pt"

TIME_ZONE = "Africa/Luanda"

USE_I18N = True

USE_TZ = True


# ============================================================
# ARQUIVOS STATIC
# ============================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# ARQUIVOS MEDIA
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# STORAGE
# ============================================================

if not DEBUG:

    STORAGES = {

        "default": {
            "BACKEND":
                "django.core.files.storage.FileSystemStorage",
        },

        "staticfiles": {
            "BACKEND":
                "django.contrib.staticfiles.storage."
                "ManifestStaticFilesStorage",
        },
    }


# ============================================================
# ============================================================
# AGROIA - CONFIGURAÇÃO DA API DE INTELIGÊNCIA ARTIFICIAL
# ============================================================
# ============================================================

# IMPORTANTE:
#
# O Django NÃO carrega o model.keras.
#
# O modelo e as classes ficam exclusivamente na AgroIA-API.
#
# Django envia:
#
#     POST /analisar
#
# para a API FastAPI.
#
# Ambiente local:
#
#     Django  -> 8000
#     FastAPI -> 8001
#
# Portanto:
#
#     http://127.0.0.1:8001/analisar
#
# Em produção, basta definir AGROIA_API_URL no ambiente.
# ============================================================

AGROIA_API_URL = os.environ.get(
    "AGROIA_API_URL",
    "http://127.0.0.1:8001/analisar"
)


# Tempo máximo para aguardar a resposta da IA.
#
# A primeira análise pode demorar mais porque a API pode
# precisar carregar o modelo TensorFlow.
#
AGROIA_API_TIMEOUT = int(
    os.environ.get(
        "AGROIA_API_TIMEOUT",
        "120"
    )
)


# ============================================================
# LOGIN / LOGOUT
# ============================================================

LOGIN_URL = "/login/"

LOGIN_REDIRECT_URL = "/"

LOGOUT_REDIRECT_URL = "/"


# ============================================================
# EMAIL
# ============================================================

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)


# ============================================================
# SESSÃO
# ============================================================

SESSION_COOKIE_AGE = 1209600

SESSION_EXPIRE_AT_BROWSER_CLOSE = False


if not DEBUG:

    SESSION_COOKIE_SECURE = True

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"


# ============================================================
# CSRF
# ============================================================

CSRF_COOKIE_HTTPONLY = False


CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        ""
    ).split(",")
    if origin.strip()
]


# ============================================================
# SEGURANÇA HTTPS
# ============================================================

if not DEBUG:

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = True

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = False


# ============================================================
# HEADERS DE SEGURANÇA
# ============================================================

X_FRAME_OPTIONS = "DENY"

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_REFERRER_POLICY = "same-origin"


# ============================================================
# DEFAULT AUTO FIELD
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
