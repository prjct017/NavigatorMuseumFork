"""Конфигурация приложения"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Файлы данных
CATALOG_FILE = os.path.join(DATA_DIR, 'catalog.json')
PERMANENT_FILE = os.path.join(DATA_DIR, 'permanent_items.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
PARSER_IMAGES_FILE = os.path.join(DATA_DIR, 'parser_images.json')

# FTP парсер
FTP_BASE_URL = 'http://192.168.3.78:8085/vm/'
PARSER_MAX_DEPTH = 10
PARSER_TIMEOUT = 30

# Безопасность
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'None')
PERMANENT_SESSION_LIFETIME = 3600

# CSRF
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600
WTF_CSRF_SSL_STRICT = False

# Rate limiting
RATELIMIT_STORAGE_URI = "memory://"
RATELIMIT_DEFAULT = ["1000 per hour", "100 per minute"]
RATELIMIT_LOGIN = "10 per minute"
RATELIMIT_ENABLED = True

# Конфигурация ERROR_LOG_FILE для логов ошибок парсера
ERROR_LOG_FILE = os.path.join(DATA_DIR, 'parser_errors.log')

# Flask-Login
LOGIN_VIEW = 'login'  # Имя маршрута для перенаправления неавторизованных пользователей
# При использовании ProxyFix и PathPrefixMiddleware Flask автоматически добавит префикс /navigator
LOGIN_MESSAGE = 'Пожалуйста, войдите для доступа к этой странице'
SESSION_PROTECTION = 'strong'
