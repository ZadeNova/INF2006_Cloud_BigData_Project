"""Environment-driven configuration. Compose is local-only; production is fail-closed."""
import os
import ipaddress
import re
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

from config.secrets import APP_FIELDS, load_environment

ENVIRON = os.environ
BASE_DIR = Path(__file__).resolve().parent.parent

def required(name):
    value = ENVIRON.get(name, "")
    if not value or value.startswith("replace-"):
        raise ImproperlyConfigured(f"{name} must be set to a non-placeholder value")
    return value

def boolean(name, default=False):
    value = ENVIRON.get(name, str(default)).lower()
    if value not in {"true", "false"}:
        raise ImproperlyConfigured(f"{name} must be true or false")
    return value == "true"

ENVIRONMENT = ENVIRON.get("DJANGO_ENV", "production")
if ENVIRONMENT not in {"local", "production"}:
    raise ImproperlyConfigured("DJANGO_ENV must be local or production")
LOCAL = ENVIRONMENT == "local"
DEBUG = boolean("DJANGO_DEBUG")
if DEBUG and not LOCAL:
    raise ImproperlyConfigured("DEBUG is forbidden outside local development")
try:
    ENVIRON = load_environment(APP_FIELDS)
except ValueError as error:
    raise ImproperlyConfigured(str(error)) from None
SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must contain at least 50 characters")
RELEASE_ID = ENVIRON.get("APP_RELEASE_ID", "local" if LOCAL else "")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", RELEASE_ID):
    raise ImproperlyConfigured("APP_RELEASE_ID must be a nonsecret release identifier")
HEALTH_PROBE_HOST = ENVIRON.get("DJANGO_HEALTH_PROBE_HOST", "")
if HEALTH_PROBE_HOST:
    try:
        address, port = HEALTH_PROBE_HOST.split(":")
        ip = ipaddress.IPv4Address(address)
        if str(ip) != address or not ip.is_private or ip.is_unspecified or ip.is_multicast or port != "8000":
            raise ValueError()
    except ValueError:
        raise ImproperlyConfigured("DJANGO_HEALTH_PROBE_HOST must be one private IPv4 address:8000") from None
ALLOWED_HOSTS = [v.strip() for v in required("DJANGO_ALLOWED_HOSTS").split(",") if v.strip()]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Explicit allowed hosts are required")
CSRF_TRUSTED_ORIGINS = [v.strip() for v in ENVIRON.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if v.strip()]
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
    "config", "accounts", "catalogue", "cart", "orders", "reporting",
]
MIDDLEWARE = [
    "config.middleware.DatabaseUnavailableMiddleware",
    # After DatabaseUnavailableMiddleware so its process_exception sees an exception first (they run in
    # reverse order) and can record the class before the 503 is produced.
    "config.middleware.RequestLoggingMiddleware",
    # Correlate Host/security rejections as well as normal requests; the exact probe stays DB-independent.
    "config.middleware.HealthProbeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]}}]
from config.database import connection_parameters
try:
    database = connection_parameters(environ=ENVIRON)
except ValueError as error:
    raise ImproperlyConfigured(str(error)) from None
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql",
    "NAME": database.pop("dbname"), "USER": database.pop("user"),
    "PASSWORD": database.pop("password"), "HOST": database.pop("host"),
    "PORT": database.pop("port", "5432"), "CONN_MAX_AGE": 60,
    "CONN_HEALTH_CHECKS": True, "OPTIONS": {**database, "connect_timeout": 3},
}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Singapore"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 1209600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not LOCAL
CSRF_COOKIE_SECURE = not LOCAL
SECURE_SSL_REDIRECT = not LOCAL
# Short by default: a browser that has seen HSTS refuses HTTP and certificate-warning bypasses for this long.
HSTS_SECONDS = ENVIRON.get("DJANGO_HSTS_SECONDS", "3600")
if not (HSTS_SECONDS.isascii() and HSTS_SECONDS.isdigit()):
    raise ImproperlyConfigured("DJANGO_HSTS_SECONDS must be a non-negative whole number")
SECURE_HSTS_SECONDS = 0 if LOCAL else int(HSTS_SECONDS)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
# Enable only behind a proxy that strips/replaces the forwarded header.
if boolean("DJANGO_TRUST_PROXY"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/products/"
LOGOUT_REDIRECT_URL = "/products/"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEMO_NAMESPACE = "synthetic/shoes/revision-a/demo/v1"

# One JSON line per event on standard output (collected by Docker and CloudWatch). Only our own request and
# error loggers, Django's 5xx error records and Django's security warnings are routed here; the formatter
# never emits exception messages. Gunicorn's access log stays disabled.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "config.jsonlog.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "stream": "ext://sys.stdout", "formatter": "json"}},
    "loggers": {
        "northstar": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
