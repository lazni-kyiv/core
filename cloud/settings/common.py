from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import os
from django.templatetags.static import static

load_dotenv()
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Security ───────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = []

VERSION="1.0.0"

# ── Apps ───────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "access.User"

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_json_widget",
    'import_export',
    "corsheaders",
    "access",
    "guests",
    "cloud",
    "services",
    "bookings",
    "dogovir",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'cloud.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = "cloud.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "dist",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cloud.wsgi.application"

# ── Internationalization ───────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"

USE_TZ = False
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True

# ── Email ──────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── Static files ───────────────────────────────────────────────────────────
STATIC_URL = "/assets/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "dist" / "assets",  # Vue assets
]
STATIC_ROOT = BASE_DIR / "staticfiles"  # 👈 сюда collectstatic
# ── Default PK ─────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── JWT ────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
}

# ── REST Framework ─────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "access.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "5/minute",
        "login": "5/minute",
        "change_password": "1/hour",
        "change_pin": "1/hour",
    },
}

# ── CORS ───────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = []
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "access",
    "content-type",
    "x-csrftoken",
]

# ── Unfold ─────────────────────────────────────────────────────────────────
UNFOLD = {
    "SITE_TITLE": "Lazni Core",
    "SITE_HEADER": "Lazni Core v2.2.1",
    "SITE_SYMBOL": "temp_preferences_eco",
    "THEME": "light",
   "SITE_LOGO": "/static/logo.png",
    "SITE_ICON": "/static/logo.png", # both modes, optimise for 32px height
    "LOGIN": {
        "image": lambda request: static("/logo.png"),
    },
    "STYLES": [
        lambda request: static("css/admin.css"),
    ],
    "COLORS": {
        "primary": {
            "50": "232 245 244",
            "100": "197 222 221",
            "200": "122 191 186",
            "400": "36 87 81",
            "500": "29 70 65",
            "600": "29 70 65",
            "700": "22 53 48",
            "800": "16 39 36",
            "900": "10 26 24",
        },
    },
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Авторизація",
                "separator": True,
                "items": [
                    {"title": "Користувачі", "icon": "person", "link": "/tech/access/user/"},
                    {"title": "Групи", "icon": "group", "link": "/tech/auth/group/"},
                    {"title": "Активні токени", "icon": "token", "link": "/tech/access/activetoken/"},
                   
                   
                ],
            },
            {
                "title": "Дані",
                "separator": True,
                "items": [
                    {"title": "Гості", "icon": "group", "link": "/tech/guests/guest/"},
                   
                    {"title": "Бронювання", "icon": "calendar_month", "link": "/tech/bookings/booking/"},
                   
                    {"title": "Договір", "icon": "assignment", "link": "/tech/dogovir/dogovirtext/"},
                      {"title": "Послуги", "icon": "spa", "link": "/tech/services/service/"},
                    {"title": "Крамниця", "icon": "store", "link": "/tech/services/kramitem/"},
                    {"title": "Комплекси", "icon": "category", "link": "/tech/services/complex/"},
                    {"title": "Пропарки", "icon": "whatshot", "link": "/tech/services/authorspecial/"},
                ],
            },
              {
                "title": "Безпека",
                "separator": True,
                "items": [
                    {
                        "title": "Request Log",
                        "icon": "monitoring",
                        "link": "/tech/cloud/requestlog/",
                    },
                    {
                        "title": "Request Analytics",
                        "icon": "monitoring",
                        "link": "/tech/cloud/requestlog/analytics/",
                    },
                    {"title": "Авторизація", "icon": "shield", "link": "/tech/security-dashboard/"},
                     {"title": "Логи авторизації", "icon": "history", "link": "/tech/access/loginlog/"},
                     {"title": "Логи бронювань", "icon": "history", "link": "/tech/bookings/bookinglog/"},
                      {"title": "Логи гостей", "icon": "history", "link": "/tech/guests/guestlog/"},

                ],
            },
          
        ],
    },
}


# ── Dogovir ────────────────────────────────────────────────────────────────
DOGOVIR_DRIVE_CREDENTIALS = BASE_DIR / "creds" / os.getenv("DOGOVIR_DRIVE_CREDENTIALS")
DOGOVIR_DRIVE_PARENT_ID = os.getenv("DOGOVIR_DRIVE_PARENT_ID")
DOGOVIR_FONT_DIR = BASE_DIR / "fonts"

# Telegram defaults (will be overridden in each env)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Google
GOOGLE_CALENDAR_ID = ""

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique",
    }
}