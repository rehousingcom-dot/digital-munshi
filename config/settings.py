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
                "apps.core.context.seo",
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

# --- Cloudinary media storage (Railway disk ephemeral hai — uploads persist karne ke liye) ---
# Jab teeno env vars set ho, item photos/logo/signature Cloudinary pe jaate hain (permanent).
# Warna local FileSystem (dev). Secret sirf Railway env me — code me nahi.
CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY = env("CLOUDINARY_API_KEY", default="")
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET", default="")
_USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)
if _USE_CLOUDINARY:
    INSTALLED_APPS += ["cloudinary", "cloudinary_storage"]
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "API_KEY": CLOUDINARY_API_KEY,
        "API_SECRET": CLOUDINARY_API_SECRET,
    }

_default_storage = ("cloudinary_storage.storage.MediaCloudinaryStorage"
                    if _USE_CLOUDINARY else "django.core.files.storage.FileSystemStorage")
_static_storage = ("whitenoise.storage.CompressedManifestStaticFilesStorage"
                   if _WHITENOISE else "django.contrib.staticfiles.storage.StaticFilesStorage")
STORAGES = {
    "default": {"BACKEND": _default_storage},
    "staticfiles": {"BACKEND": _static_storage},
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

# Resend (HTTPS email API) — Railway blocks outbound SMTP, so we send email over HTTPS.
# Sign up free at resend.com, put the key here. From-address must be a verified domain
# (e.g. noreply@reloaddigital.in) or "onboarding@resend.dev" for testing to your own inbox.
RESEND_API_KEY = env("RESEND_API_KEY", default="")
RESEND_FROM = env("RESEND_FROM", default="Digital Munshi <onboarding@resend.dev>")

# Backup email (backup_db command link yahan bhejta hai; khaali = DEFAULT_FROM_EMAIL)
BACKUP_EMAIL = env("BACKUP_EMAIL", default="")

# --- Sentry error monitoring (optional) — SENTRY_DSN env set karo to enable ---
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN and not DEBUG:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment="production",
        )
    except Exception:
        pass  # sentry optional — kabhi boot na roke

# --- SMS gateway (DLT) — provider-agnostic. Set SMS_API_URL to enable. ---
# Example (GET): https://gateway.com/api?key=XXX&sender=RELOAD&to={to}&message={text}&tempid={tid}
SMS_API_URL = env("SMS_API_URL", default="")
SMS_METHOD = env("SMS_METHOD", default="GET")
SMS_OTP_TEXT = env("SMS_OTP_TEXT", default="Your Digital Munshi OTP is {otp}. Valid 10 min. Do not share.")
SMS_OTP_TID = env("SMS_OTP_TID", default="")

# Marketing: naye leads is email par notify honge (Resend). Khaali = BACKUP_EMAIL.
LEADS_EMAIL = env("LEADS_EMAIL", default="rehousing.com@gmail.com")

# Analytics + support (marketing pages). Set in env to enable.
GA_MEASUREMENT_ID = env("GA_MEASUREMENT_ID", default="")
SUPPORT_WHATSAPP = env("SUPPORT_WHATSAPP", default="")
