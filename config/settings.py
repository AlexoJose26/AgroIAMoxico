from pathlib import Path
import os



BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-this"
)



DEBUG = os.environ.get(
    "DEBUG",
    "True"
).lower() == "true"



ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost"
    ).split(",")
    if host.strip()
]

INSTALLED_APPS = [

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "inicio",
    "produtos",
    "categorias",
    "diagnostico",
]


MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"



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


WSGI_APPLICATION = "config.wsgi.application"


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


LANGUAGE_CODE = "pt-pt"


TIME_ZONE = "Africa/Luanda"



USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"


STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


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


MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "/login/"

LOGIN_REDIRECT_URL = "/"

LOGOUT_REDIRECT_URL = "/"


EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)


SESSION_COOKIE_AGE = 1209600


SESSION_EXPIRE_AT_BROWSER_CLOSE = False


if not DEBUG:

    SESSION_COOKIE_SECURE = True

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"


CSRF_COOKIE_HTTPONLY = False


CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        ""
    ).split(",")
    if origin.strip()
]



if not DEBUG:

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = True

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = False



X_FRAME_OPTIONS = "DENY"


SECURE_CONTENT_TYPE_NOSNIFF = True


SECURE_REFERRER_POLICY = "same-origin"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
