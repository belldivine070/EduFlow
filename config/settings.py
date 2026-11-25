from datetime import timedelta
import os
import warnings
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from django.contrib.messages import constants as _m
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# ENVIRONMENT & MODE SWITCH (Toggle between 'development' and 'production')
# ==============================================================================
RUN_MODE = os.getenv("DJANGO_RUN_MODE", "development").strip().lower()
if RUN_MODE not in {"development", "production"}:
    raise ImproperlyConfigured("DJANGO_RUN_MODE must be 'development' or 'production'.")

# Safe parsing helpers
def env_bool(var_name, default=False):
    return os.getenv(var_name, str(default)).lower() in ("true", "1", "t", "yes")

def env_int(var_name, default=0):
    try:
        return int(os.getenv(var_name, default))
    except (TypeError, ValueError):
        return default

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
AI_API_KEY = os.getenv("AI_API_KEY", "")
ADMIN_URL = os.getenv("DJANGO_ADMIN_URL", "django-admin/")
TRUSTED_PROXY_COUNT = env_int("TRUSTED_PROXY_COUNT", 0)

# ==============================================================================
# COMMON CORE SETTINGS
# ==============================================================================
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "daphne",
    "channels",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "axes",
    "accounts",
    "core",
    "schools",
    "subscriptions",
    "academics",
    "staff",
    "assessments",
    "examinations",
    "learning",
    "admissions",
    "finance",
    "store",
    "communications",
    "support",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.tenant.SubdomainTenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SiteHitMiddleware",
    "accounts.middleware.AccountStateMiddleware",
    "axes.middleware.AxesMiddleware",  # must be last
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'core.context_processors.app_settings_processor', 
                "core.context_processors.school",
                "core.context_processors.staff_navigation",
                "academics.context_processors.academic_period",
            ],
        },
    },
]

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "accounts.backends.MultiIdentifierBackend",
]

# Number of seconds to wait before updating a user's last active timestamp again
LAST_ACTIVITY_WRITE_SECONDS = 60
ONE_TIME_PASSWORD_LENGTH = 8

# File upload limits in bytes (50 MB = 50 * 1024 * 1024 bytes)
UPLOAD_LIMITS = {
    "image": 50 * 1024 * 1024,     # 50 MB limit for images
    "document": 50 * 1024 * 1024,  # 50 MB limit for documents
    "video": 500 * 1024 * 1024,    # 500 MB limit for videos (adjust as needed)
    "audio": 50 * 1024 * 1024,     # 50 MB limit for audio
}

# Security & Session Standards
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = BASE_DIR / "media" / "private"

STORAGES = {
    "default": {"BACKEND": "core.storage.DefaultPublicStorage"},
    "private": {"BACKEND": "core.storage.PrivateFileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

from datetime import timedelta

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Nigerian School Management SaaS API",
    "DESCRIPTION": "Production-grade multi-tenant REST API for Nigerian primary and secondary schools.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "ExamStatusEnum": "examinations.models.Exam.Status",
        "StudentExamAttemptStatusEnum": "examinations.models.StudentExamAttempt.Status",
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ==============================================================================
# MODE-SPECIFIC CONFIGURATIONS (Dev vs Prod)
# ==============================================================================

if RUN_MODE == "production":
    # --- PRODUCTION CONFIGURATION ---
    DEBUG = False
    ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
    
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production.")
    if "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Wildcard ALLOWED_HOSTS is not allowed in production.")
    if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("insecure"):
        raise ImproperlyConfigured("Set a long random DJANGO_SECRET_KEY in production.")

    # Proxy & SSL Security Headers
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    CSRF_TRUSTED_ORIGINS = [
        origin.strip() for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
        if origin.strip()
    ]

    # Production requires PostgreSQL; persistent connections can sit behind PgBouncer.
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ImproperlyConfigured("DATABASE_URL must be set in production.")
    DATABASES = {
        "default": dj_database_url.config(default=database_url, conn_max_age=600)
    }
    if DATABASES["default"].get("ENGINE") != "django.db.backends.postgresql":
        raise ImproperlyConfigured("Production DATABASE_URL must use PostgreSQL.")
    DATABASES["default"]["ATOMIC_REQUESTS"] = False
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

    # Email & Caching (Production SMTP & DB Cache)
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "")
    EMAIL_PORT = env_int("EMAIL_PORT", 587)
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "School <noreply@school.com>")

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache",
        }
    }

    # Real-Time Channels Layer (Production Redis / Fallback)
    REDIS_URL = os.getenv("REDIS_URL", "")
    if REDIS_URL:
        CHANNEL_LAYERS = {
            "default": {
                "BACKEND": "channels_redis.core.RedisChannelLayer",
                "CONFIG": {"hosts": [REDIS_URL]},
            }
        }
    else:
        warnings.warn(
            "REDIS_URL is not set; the in-memory Channels layer only supports single-process deployments.",
            RuntimeWarning,
            stacklevel=2,
        )
        CHANNEL_LAYERS = {
            "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
        }

    STORAGES["staticfiles"] = {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    }

    # Optional Cloudinary Storage integration
    if env_bool("USE_CLOUDINARY", False):
        STORAGES["default"] = {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        }

    # Optional S3 Storage integration
    elif env_bool("USE_S3", False):
        if not os.getenv("AWS_STORAGE_BUCKET_NAME"):
            raise ImproperlyConfigured("AWS_STORAGE_BUCKET_NAME is required when USE_S3 is enabled.")
        _s3 = {
            "bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "region_name": os.getenv("AWS_S3_REGION_NAME", None),
            "file_overwrite": False,
        }
        STORAGES["default"] = {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {**_s3, "location": "public", "default_acl": "public-read", "querystring_auth": False},
        }
        STORAGES["private"] = {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {**_s3, "location": "private", "default_acl": "private", "querystring_auth": True, "querystring_expire": 120},
        }

else:
    # --- DEVELOPMENT CONFIGURATION ---
    DEBUG = True
    ALLOWED_HOSTS = [".localhost", "localhost", "127.0.0.1", "testserver"]

    # SQLite is the default local development database so contributors can run the
    # project without a PostgreSQL service. A DATABASE_URL override works if
    # a Postgres instance is available and reachable.
    import socket
    import sys

    database_url = os.getenv("DATABASE_URL", "").strip()
    use_sqlite = False

    if not database_url:
        use_sqlite = True
    else:
        # Test if PostgreSQL host/port is reachable
        try:
            parsed_db = dj_database_url.parse(database_url)
            engine = parsed_db.get("ENGINE", "")
            if "postgresql" in engine or database_url.startswith("postgres"):
                host = parsed_db.get("HOST") or "localhost"
                port = int(parsed_db.get("PORT") or 5432)
                with socket.create_connection((host, port), timeout=0.8):
                    pass
        except Exception:
            warnings.warn(
                f"Configured database at {database_url} is unreachable. Falling back to SQLite for development/testing.",
                RuntimeWarning,
                stacklevel=2,
            )
            use_sqlite = True

    default_database = (
        f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
        if use_sqlite
        else database_url
    )
    if use_sqlite:
        os.environ["DATABASE_URL"] = default_database
    DATABASES = {"default": dj_database_url.parse(default_database, conn_max_age=600)}
    DATABASES["default"]["ATOMIC_REQUESTS"] = False

    # Email console backend for local debugging
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "School <noreply@localhost>"

    # Channels Layer (InMemory fallback, or Redis if configured)
    REDIS_URL = os.getenv("REDIS_URL", "")
    if REDIS_URL and not env_bool("USE_INMEMORY_CHANNELS", False):
        CHANNEL_LAYERS = {
            "default": {
                "BACKEND": "channels_redis.core.RedisChannelLayer",
                "CONFIG": {"hosts": [REDIS_URL]},
            }
        }
    else:
        CHANNEL_LAYERS = {
            "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
        }

    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    