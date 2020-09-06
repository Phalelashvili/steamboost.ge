import os
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = ''

DEBUG = False

ALLOWED_HOSTS = ['steamboost.ge']

SOCIAL_AUTH_STEAM_API_KEY = ''
SOCIAL_AUTH_STEAM_EXTRA_DATA = ['player']
AUTH_USER_MODEL = 'main.User'

ABSOLUTE_URL = 'https://steamboost.ge/'

APPEND_SLASH = False

JET_MODULE_GOOGLE_ANALYTICS_CLIENT_SECRETS_FILE = os.path.join(
    BASE_DIR, 'client_secrets.json')

RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_PUBLIC_KEY = ''

DISCORD_INVITE = ''

REDIRECT_URL = random.choice([
    'https://www.google.com/search?q=furry+porn',                        # google search -- fury porn
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=43',                  # rickroll
    'https://www.youtube.com/watch?v=5HDkiUCYTio&feature=youtu.be&t=21', # epic georgian hacking
    'https://www.youtube.com/watch?v=o7x_CZILTXg&feature=youtu.be&t=41', # macarena
    'https://www.youtube.com/watch?v=LDU_Txk06tM&feature=youtu.be&t=75', # crab rave
    'https://www.youtube.com/watch?v=stlZEKoJg10&feature=youtu.be&t=18', # Soviet National Anthem Earrape
    'https://www.youtube.com/watch?v=Q3E7L_RoyTU'                        # Thomas The Tank Engine Earrape
])

API_KEY = ''
BOOST_ENCRYPTION_KEY = ''
SUSI_PASSWORD = ''

MAINTENANCE_MODE_IGNORE_SUPERUSER = True
MAINTENANCE_MODE_IGNORE_STAFF = True
MAINTENANCE_MODE_IGNORE_ADMIN_SITE = True
MAINTENANCE_MODE_STATUS_CODE = 200  # doesn't fucking work

# dirty way to enable some functionality
MAINTENANCE_MODE_IGNORE_URLS = ('/login/', '/complete/', '/logout',
                                '/notifications', '/ajax/notifications', '/webpush/',
                                '/code/', '/susi/', '/extension/', '/pizza/', '/faq')

INSTALLED_APPS = [
    'maintenance_mode',
    'jet.dashboard',
    'jet',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'main',
    'boost',
    'pizza',
    'extensions',
    'susi',

    'social_core',
    'social_django',
    'webpush',
]


WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": "",
    "VAPID_PRIVATE_KEY": "",
    "VAPID_ADMIN_EMAIL": "",
}

AUTHENTICATION_BACKENDS = [

    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.steam.SteamOpenId',

]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'maintenance_mode.middleware.MaintenanceModeMiddleware',
    'main.middleware.CORSMiddleware'
]

MIDDLEWARE_CLASSES = (
    # https://warehouse.python.org/project/whitenoise/
    # 'whitenoise.middleware.WhiteNoiseMiddleware',
)


LOGIN_REDIRECT_URL = '/'
ROOT_URLCONF = 'base.urls'

APPEND_SLASH = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'maintenance_mode.context_processors.maintenance_mode',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'base.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'steamboost',
        'USER': 'postgres',
        'PASSWORD': 'diT59%w1gQK$ptI1bvGP',
        'HOST': 'localhost',
        'PORT': '5432',
    },
    'steamtracker': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'steamtracker',
        'USER': 'postgres',
        'PASSWORD': 'diT59%w1gQK$ptI1bvGP',
        'HOST': 'localhost',
        'PORT': '5432',
    },
    'pizza': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'pizza',
        'USER': 'postgres',
        'PASSWORD': 'diT59%w1gQK$ptI1bvGP',
        'HOST': 'localhost',
        'PORT': '5432',
    },
    'susi': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'susi',
        'USER': 'postgres',
        'PASSWORD': 'diT59%w1gQK$ptI1bvGP',
        'HOST': 'localhost',
        'PORT': '5432',
    }

}


LOGIN_URL = '/login/steam/'


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGES = (
    ('en-us', ('English')),
    ('ka', ('Georgian')),
)

LANGUAGE_CODE = 'ka'

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale')
]

TIME_ZONE = 'Asia/Tbilisi'

USE_I18N = True

USE_L10N = True

USE_TZ = False

JET_THEMES = [
    {
        'theme': 'default',  # theme folder name
        'color': '#47bac1',  # color of the theme's button in user menu
        'title': 'Default'   # theme title
    },
    {
        'theme': 'green',
        'color': '#44b78b',
        'title': 'Green'
    },
    {
        'theme': 'light-green',
        'color': '#2faa60',
        'title': 'Light Green'
    },
    {
        'theme': 'light-violet',
        'color': '#a464c4',
        'title': 'Light Violet'
    },
    {
        'theme': 'light-blue',
        'color': '#5EADDE',
        'title': 'Light Blue'
    },
    {
        'theme': 'light-gray',
        'color': '#222',
        'title': 'Light Gray'
    }
]

# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'base/static/')
STATIC_URL = '/static/'
