import dj_database_url
import os
import pymysql
pymysql.install_as_MySQLdb()

DEFAULT_DATABASE_URL = "mysql://localhost:{port}/django_db_queue".format(
    port=os.getenv('DATABASE_PORT', 3306)
)

DATABASES = {
    'default': dj_database_url.config(default=DEFAULT_DATABASE_URL),
}

INSTALLED_APPS = (
    'django_dbq',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

SECRET_KEY = 'abcde12345'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django_dbq': {
            'level': 'CRITICAL',
            'propagate': True,
        },
    }
}
