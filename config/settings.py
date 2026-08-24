from pathlib import Path


# ============================================================
# CAMINHO BASE DO PROJETO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SEGURANÇA
# ============================================================

SECRET_KEY = (
    "django-insecure-tz!bbh1ouys&b3#cqddhd%t+6^@^3=+b6gdfj"
    "$s0)i^_)ts+(*"
)

DEBUG = True


# ============================================================
# HOSTS PERMITIDOS
# ============================================================

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]


# ============================================================
# APLICAÇÕES INSTALADAS
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
    "culturas",
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
        # Templates globais do projeto
        # ----------------------------------------------------

        "DIRS": [
            BASE_DIR / "templates",
        ],

        # ----------------------------------------------------
        # Permite procurar templates dentro das apps:
        #
        # categorias/templates/categorias/
        # culturas/templates/culturas/
        # inicio/templates/inicio/
        # diagnostico/templates/diagnostico/
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

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Diretório utilizado quando executares collectstatic.
STATIC_ROOT = BASE_DIR / "staticfiles"


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

# Em desenvolvimento os e-mails aparecem no terminal.

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
# CSRF
# ============================================================

CSRF_COOKIE_HTTPONLY = False


# ============================================================
# SEGURANÇA DO NAVEGADOR
# ============================================================

X_FRAME_OPTIONS = "DENY"


# ============================================================
# CHAVE PRIMÁRIA PADRÃO
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
