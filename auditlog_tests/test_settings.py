"""
Settings file for the Auditlog test suite.
"""
import os

DEBUG = True

SECRET_KEY = "test"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.admin",
    "django.contrib.staticfiles",
    "auditlog",
    "auditlog_tests",
]

MIDDLEWARE = (
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("TEST_DB_NAME", "auditlog_tests_db"),
    }
}

TEMPLATES = [
    {
        "APP_DIRS": True,
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    },
]

STATIC_URL = "/static/"

ROOT_URLCONF = "auditlog_tests.urls"

USE_TZ = True
