"""Утилиты для работы с данными"""
import os
import json
from datetime import datetime
from urllib.parse import unquote


def ensure_data_dir(data_dir):
    """Создать директорию если не существует"""
    os.makedirs(data_dir, exist_ok=True)


def decode_url(url):
    """Декодировать URL из %XX формата в читаемый вид"""
    return unquote(url) if url else url


def normalize_url(url):
    """Нормализовать URL: убрать пробелы, заменить http:// на https://"""
    if not url:
        return url
    url = url.strip()
    return 'https://' + url[7:] if url.startswith('http://') else url


def replace_url_domain(url, old_domain='192.168.3.78:8085', new_domain='vm-ftp.anosov.ru'):
    """Заменить домен в URL"""
    return url.replace(old_domain, new_domain) if url else url


def load_json_file(file_path, default=None):
    """Загрузить JSON файл или вернуть значение по умолчанию"""
    if default is None:
        default = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default


def save_json_file(file_path, data):
    """Сохранить данные в JSON файл"""
    ensure_data_dir(os.path.dirname(file_path))
    
    def decode_urls_in_data(obj):
        if isinstance(obj, dict):
            return {key: decode_url(value) if key in ('url', 'icon') and isinstance(value, str) else decode_urls_in_data(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [decode_urls_in_data(item) for item in obj]
        return obj
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(decode_urls_in_data(data), f, ensure_ascii=False, indent=2)


def get_current_timestamp():
    """Получить текущую дату и время в формате YYYY-MM-DD HH:MM"""
    return datetime.now().strftime('%Y-%m-%d %H:%M')


def get_full_timestamp():
    """Получить полную дату и время в формате YYYY-MM-DD HH:MM:SS"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def load_users(users_file, hash_password_func):
    """Загрузить пользователей из JSON файла"""
    default_username = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
    default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
    return load_json_file(users_file, default={
        "users": [{
            "id": 1,
            "username": default_username,
            "password_hash": hash_password_func(default_password),
            "is_admin": True,
            "created_at": datetime.now().isoformat(),
        }]
    })


def load_catalog(catalog_file):
    """Загрузить каталог из JSON файла"""
    return load_json_file(catalog_file, default={"name": "ВЕБ-РЕСУРСЫ МУЛЬТИМЕДИЙНОГО КОНТЕНТА ПО НАПРАВЛЕНИЯМ", "icon": "folder.png", "children": []})


# Обёртки для сохранения
save_users = lambda f, d: save_json_file(f, d)
save_catalog = lambda f, d: save_json_file(f, d)
load_permanent_items = lambda f: load_json_file(f, default={"permanent_items": []})
save_permanent_items = lambda f, d: save_json_file(f, d)
