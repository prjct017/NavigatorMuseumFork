"""
Модуль утилит для аутентификации и управления пользователями.

Предоставляет функции для:
- Хранения данных пользователя (класс User)
- Хеширования и проверки паролей (bcrypt)
- Создания новых пользователей
- Ограничения доступа к административным функциям
"""
import bcrypt
from datetime import datetime
from functools import wraps

from flask import flash, redirect, request, jsonify
from flask_login import UserMixin, current_user


class User(UserMixin):
    """
    Класс пользователя для интеграции с Flask-Login.
    
    Атрибуты:
        id (int): Уникальный идентификатор пользователя
        username (str): Имя пользователя
        is_admin (bool): Флаг администратора
    """
    
    def __init__(self, user_id, username, is_admin=False):
        """
        Инициализация пользователя.
        
        Args:
            user_id: Уникальный ID пользователя
            username: Имя пользователя
            is_admin: Права администратора (по умолчанию False)
        """
        self.id = user_id
        self.username = username
        self.is_admin = is_admin
    
    def get_id(self):
        """Возвращает ID пользователя в виде строки (требуется Flask-Login)."""
        return str(self.id)


def hash_password(password):
    """
    Хеширует пароль с использованием bcrypt.
    
    Args:
        password (str): Пароль в открытом виде
        
    Returns:
        str: Хешированный пароль
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password, password_hash):
    """
    Проверяет соответствие пароля хешу.
    
    Args:
        password (str): Пароль в открытом виде
        password_hash (str): Хешированный пароль для сравнения
        
    Returns:
        bool: True если пароль верный, False иначе
    """
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        # При любой ошибке (некорректный хеш и т.п.) возвращаем False
        return False


def create_user(username, password, is_admin=False):
    """
    Создаёт структуру данных нового пользователя.
    
    Args:
        username (str): Имя пользователя
        password (str): Пароль в открытом виде (будет захеширован)
        is_admin (bool): Права администратора
        
    Returns:
        dict: Словарь с данными пользователя
    """
    return {
        "id": None,  # ID будет назначен при сохранении
        "username": username,
        "password_hash": hash_password(password),
        "is_admin": is_admin,
        "created_at": datetime.now().isoformat()
    }


def admin_required_decorator(func):
    """
    Декоратор для ограничения доступа к функциям только для администраторов.
    
    Если пользователь не авторизован или не является администратором:
    - Для API запросов (/api/*) возвращается JSON 401
    - Для обычных запросов выполняется редирект на страницу входа
    
    Args:
        func: Декорируемая функция-обработчик
        
    Returns:
        wrapped_function: Обёрнутая функция с проверкой прав
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Проверка: пользователь авторизован И является администратором
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            
            # Для API endpoints возвращаем JSON ошибку вместо редиректа
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Требуется авторизация администратора',
                    'status': 'unauthorized'
                }), 401
            
            # Для обычных запросов показываем сообщение и перенаправляем на login
            flash('Требуется права администратора', 'error')
            
            # Получаем префикс пути из окружения (устанавливается middleware/nginx)
            script_name = request.environ.get('SCRIPT_NAME', '').rstrip('/')
            
            # Если префикс не указан, используем значение по умолчанию
            if not script_name:
                script_name = '/navigator'
            
            # Формируем URL страницы входа с префиксом
            login_url = script_name + '/login'
            
            # Добавляем параметр next для возврата на исходную страницу после входа
            full_next = script_name + request.path
            
            return redirect(f"{login_url}?next={full_next}")
        
        # Если проверка пройдена — вызываем оригинальную функцию
        return func(*args, **kwargs)
    
    return decorated_function
