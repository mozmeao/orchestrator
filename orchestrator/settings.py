# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Django settings for orchestrator project.
"""

from pathlib import Path

from everett.manager import ChoiceOf, ConfigManager, ConfigurationMissingError, ListOf

# The `basic_config` manager searches in this order:
#   1. environment variables
#   2. .env file
#   3. `default` keyword argument
config = ConfigManager.basic_config()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
try:
    # Make this unique, and don't share it with anybody.
    SECRET_KEY = config("SECRET_KEY")
except ConfigurationMissingError as exc:
    raise ValueError(
        "The SECRET_KEY environment variable is required. Move env-dist to .env if you want the defaults.",
    ) from exc

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", parser=bool, default="false")

LOG_LEVEL = config(
    "DJANGO_LOG_LEVEL",
    parser=ChoiceOf(
        str,
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    ),
    default="WARNING",
)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    parser=ListOf(str, allow_empty=False),
    default="localhost,127.0.0.1",
)


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "watchman",
    "google_marketing_platform",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "orchestrator.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "orchestrator.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Use MySQL for production, SQLite for local development
DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    # MySQL configuration for production
    # Expected format: mysql://user:password@host:port/dbname  # pragma: allowlist secret
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=config("DB_CONN_MAX_AGE", parser=int, default="600"),
            conn_health_checks=True,
        )
    }
else:
    # SQLite fallback for local development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Cache configuration
# https://docs.djangoproject.com/en/6.0/topics/cache/
REDIS_URL = config("REDIS_URL", default="")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "gtm_cache",
            "TIMEOUT": config("CACHE_TTL", parser=int, default="3200"),
        }
    }
else:
    # Fallback to local memory cache if Redis is not configured
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "gtm-cache",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

# Storage backend configuration
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Security settings
# https://docs.djangoproject.com/en/5.2/ref/settings/#security

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HTTPS settings - only enabled in production (when DEBUG is False)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# django-watchman configuration
# https://django-watchman.readthedocs.io/

WATCHMAN_CHECKS = (
    "watchman.checks.databases",
    "watchman.checks.caches",
)
