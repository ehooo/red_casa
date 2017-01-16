from red_casa.settings.prod import *

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
DATABASE_ROUTERS = ['red_casa.router.DatabaseAppsRouter']
# DATABASE_APPS_MAPPING = {'red_casa.dhcp': 'postgresql'}

DEFAULT_DNS_PORT = 5353

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
