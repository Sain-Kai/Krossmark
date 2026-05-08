from pathlib import Path
import os
import sys

# ─────────────────────────────────────────────
# BASE PATHS
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Allow Django to access vision/
PROJECT_ROOT = BASE_DIR.parent.parent
sys.path.append(str(PROJECT_ROOT))

# ─────────────────────────────────────────────
# ENV HELPER
# ─────────────────────────────────────────────
def _split_csv(env_name, default=""):
    raw = os.getenv(env_name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]

# ─────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")

DEBUG = os.getenv("DEBUG", "1") == "1"

# 🔥 FINAL FIX — NO MORE DISALLOWED HOST
ALLOWED_HOSTS = ["*"]

# Optional strict mode (use later)
"""
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "10.209.117.251",   # Laptop backend
    "10.209.117.232",   # Pi
    "10.209.117.70",    # Node2 (if needed)
]
"""

# Prevent header issues across devices
USE_X_FORWARDED_HOST = True

# ─────────────────────────────────────────────
# APPS
# ─────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "rest_framework",

    "surveillance",
]

# ─────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ─────────────────────────────────────────────
# URLS
# ─────────────────────────────────────────────
ROOT_URLCONF = "krossmark_backend.urls"

WSGI_APPLICATION = "krossmark_backend.wsgi.application"
ASGI_APPLICATION = "krossmark_backend.asgi.application"

# ─────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

# ─────────────────────────────────────────────
# INTERNATIONAL
# ─────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"

USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────────
# STATIC / MEDIA
# ─────────────────────────────────────────────
STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = _split_csv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8081"
)

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ─────────────────────────────────────────────
# CSRF FIX (IMPORTANT)
# ─────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    "http://10.209.117.251:8000",  # backend
    "http://10.209.117.232:5000",  # pi
]

# ─────────────────────────────────────────────
# DRF
# ─────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# ─────────────────────────────────────────────
# UPLOAD LIMITS
# ─────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600

# ─────────────────────────────────────────────
# AI CONFIG
# ─────────────────────────────────────────────
AI_PIPELINE = {
    "BURST_DURATION": 3,
    "FRAME_LIMIT": 120,
    "CONF_THRESHOLD": 0.6,
}