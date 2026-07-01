"""
Django settings for ERP Munshi.
Local test: SQLite (default). Server: PostgreSQL via DATABASE_URL.
"""
from pathlib import Path
from datetime import timedelta
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
)
# Read .env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "apps.tenants",
    "apps.accounts",
    "apps.core",
    "apps.inventory",
    "apps.party",
    "apps.billing",
    "apps.reports",
    "apps.payments",
    "apps.cashbank",
    "apps.accounting",
    "apps.hr",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.tenants.middleware.TenantMiddleware",
]

# WhiteNoise — production static serving. Sirf tab add karo jab package installed ho
# (taaki local dev bina whitenoise ke bhi chale). Server pe requirements se install ho jata hai.
try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")
    _WHITENOISE = True
except ImportError:
    _WHITENOISE = False

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: SQLite local, PostgreSQL on server (set DATABASE_URL in .env)
DATABASE_URL = env("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
_static_src = BASE_DIR / "static"
STATICFILES_DIRS = [_static_src] if _static_src.exists() else []
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# WhiteNoise compressed static storage — sirf jab whitenoise installed ho
if _WHITENOISE:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # JWT only — SPA Bearer token se auth karti hai. SessionAuthentication
    # hata diya taaki stray admin session cookie "CSRF Failed" na de.
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "apps.accounts.permissions.RolePermission",
    ),
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "2000/hour",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# JWT lifetimes — access token lambi (kaam ke beech logout na ho), refresh se auto-renew.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Digital Munshi ERP API",
    "DESCRIPTION": "Multi-tenant billing + inventory + GST ERP (SaaS).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Production security (DEBUG=False hone par auto-on)
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # SECURE_SSL_REDIRECT env se control (reverse-proxy ke peeche off rakh sakte hain)
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
    # CSRF trusted origins — ALLOWED_HOSTS se banao (https:// + wildcard subdomains)
    CSRF_TRUSTED_ORIGINS = [
        (f"https://*{h}" if h.startswith(".") else f"https://{h}")
        for h in ALLOWED_HOSTS if h not in ("127.0.0.1", "localhost", "*")
    ]

CORS_ALLOW_ALL_ORIGINS = DEBUG  # local dev only; server pe restrict karenge

# Razorpay — .env mein set karein. Khaali = DEV MODE (test without real payment).
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")

# Email (signup OTP, invoice email). Set these env vars to enable real sending;
# jab tak set nahi, OTP dev-mode me screen par dikhta hai.
# Gmail: EMAIL_HOST=smtp.gmail.com, EMAIL_PORT=587, EMAIL_USE_TLS=True,
#        EMAIL_HOST_USER=<gmail>, EMAIL_HOST_PASSWORD=<app password>.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=8)  # fail fast if SMTP is slow/blocked
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Digital Munshi <no-reply@digitalmunshi.in>")
