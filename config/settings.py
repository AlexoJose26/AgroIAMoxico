from pathlib import Path
import os


# ============================================================
# BASE DO PROJETO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SEGURANÇA
# ============================================================

# Em produção, configure DJANGO_SECRET_KEY na Vercel.
# Em desenvolvimento, utiliza a chave abaixo como fallback.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-this"
)


# ============================================================
# DEBUG
# ============================================================

# Localmente:
# DEBUG=True
#
# Na Vercel:
# DEBUG=False

DEBUG = os.environ.get(
    "DEBUG",
    "True"
).lower() == "true"


# ============================================================
# HOSTS PERMITIDOS
# ============================================================

# Desenvolvimento:
# 127.0.0.1,localhost
#
# Produção:
# agroia-moxico.vercel.app
#
# A variável ALLOWED_HOSTS na Vercel pode conter vários hosts
# separados por vírgula.

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost"
    ).split(",")
    if host.strip()
]


# ============================================================
# CONFIGURAÇÃO DO DJANGO
# ============================================================

INSTALLED_APPS = [

    # --------------------------------------------------------
    # Django
    # --------------------------------------------------------

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # --------------------------------------------------------
    # AgroIA Moxico
    # --------------------------------------------------------

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
# CONFIGURAÇÃO PRINCIPAL DE URLS
# ============================================================

ROOT_URLCONF = "config.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [

    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        # ----------------------------------------------------
        # Templates globais
        # ----------------------------------------------------

        "DIRS": [
            BASE_DIR / "templates",
        ],

        # ----------------------------------------------------
        # Permite procurar templates dentro das aplicações
        # ----------------------------------------------------

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
# BASE DE DADOS
# ============================================================

# O projeto utiliza SQLite localmente.
#
# Quando DATABASE_URL estiver configurada, utiliza PostgreSQL.
#
# Isto permite:
#
# Desenvolvimento:
#     SQLite
#
# Produção:
#     PostgreSQL
#
# Para PostgreSQL será necessário instalar:
#
#     dj-database-url
#     psycopg[binary]

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
# IDIOMA
# ============================================================

LANGUAGE_CODE = "pt-pt"


# ============================================================
# FUSO HORÁRIO
# ============================================================

TIME_ZONE = "Africa/Luanda"


# ============================================================
# INTERNACIONALIZAÇÃO
# ============================================================

USE_I18N = True

USE_TZ = True


# ============================================================
# FICHEIROS ESTÁTICOS
# ============================================================

STATIC_URL = "/static/"


# ------------------------------------------------------------
# Diretório de arquivos estáticos durante o desenvolvimento.
# ------------------------------------------------------------

STATICFILES_DIRS = [
    BASE_DIR / "static",
]


# ------------------------------------------------------------
# Diretório utilizado pelo collectstatic.
# ------------------------------------------------------------

STATIC_ROOT = BASE_DIR / "staticfiles"


# ------------------------------------------------------------
# ManifestStaticFilesStorage
#
# Em produção, o Django pode utilizar o manifesto dos
# arquivos estáticos.
# ------------------------------------------------------------

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
# FICHEIROS MEDIA
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# AUTENTICAÇÃO
# ============================================================

LOGIN_URL = "/login/"

LOGIN_REDIRECT_URL = "/"

LOGOUT_REDIRECT_URL = "/"


# ============================================================
# E-MAIL
# ============================================================

# ------------------------------------------------------------
# Desenvolvimento
# ------------------------------------------------------------
#
# Os e-mails são apresentados no terminal.
#
# Em produção, podemos posteriormente configurar SMTP ou outro
# serviço de e-mail através de variáveis de ambiente.
# ------------------------------------------------------------

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)


# ============================================================
# SESSÕES
# ============================================================

# 2 semanas
SESSION_COOKIE_AGE = 1209600


# Mantém a sessão mesmo depois de fechar o navegador.
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# ============================================================
# COOKIES DE SESSÃO
# ============================================================

if not DEBUG:

    SESSION_COOKIE_SECURE = True

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"


# ============================================================
# CSRF
# ============================================================

CSRF_COOKIE_HTTPONLY = False


# ------------------------------------------------------------
# Em produção, configure:
#
# CSRF_TRUSTED_ORIGINS
#
# através da variável:
#
# CSRF_TRUSTED_ORIGINS=https://agroia-moxico.vercel.app
#
# Vários endereços podem ser separados por vírgula.
# ------------------------------------------------------------

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

# Na Vercel o HTTPS é utilizado em produção.

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
# SEGURANÇA DO NAVEGADOR
# ============================================================

X_FRAME_OPTIONS = "DENY"


# ============================================================
# CONTENT TYPE
# ============================================================

SECURE_CONTENT_TYPE_NOSNIFF = True


# ============================================================
# REFERRER POLICY
# ============================================================

SECURE_REFERRER_POLICY = "same-origin"


# ============================================================
# CHAVE PRIMÁRIA PADRÃO
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
