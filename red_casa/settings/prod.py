from red_casa.settings.common import *

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
DATABASE_ROUTERS = ['red_casa.router.DatabaseAppsRouter']
# DATABASE_APPS_MAPPING = {'red_casa.dhcp': 'postgresql'}


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'red_casa',
        'USER': 'red_casa',
        'PASSWORD': 'red_casa',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
