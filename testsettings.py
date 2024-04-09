import os
import dj_database_url


DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///:memory:")

DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL),
}

INSTALLED_APPS = ("django_dbq",)

SECRET_KEY = "abcde12345"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"console": {"level": "DEBUG", "class": "logging.StreamHandler",},},
    "root": {"handlers": ["console"], "level": "INFO",},
    "loggers": {"django_dbq": {"level": "CRITICAL", "propagate": True,},},
}

USE_TZ = True
