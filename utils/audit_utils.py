"""Утилиты для системы аудита

Модуль обеспечивает автоматическое ведение журнала событий с фиксацией всех значимых параметров:
- дата и время совершения события (по часовому поясу Екатеринбург, UTC+5)
- IP-адрес источника запроса
- тип события (добавление, изменение, удаление, просмотр, экспорт, ошибка, загрузка)
- объект воздействия (идентификатор ресурса, файла и др.)

Объекты аудита:
- ошибки (error)
- успешные загрузки элементов (upload_success)
- веб-ресурсы: добавление, изменение, удаление, просмотр, экспорт (web_resource)
- файловая система: чтение (filesystem_read)
"""
import os
import json
from datetime import datetime
from functools import wraps
from flask import request, g

# Часовой пояс Екатеринбург (UTC+5)
YEKATERINBURG_OFFSET = 5 * 3600  # 5 часов в секундах


# Типы событий аудита
class AuditEventType:
    """Перечисление типов событий аудита"""
    # Ошибки
    ERROR = 'error'
    
    # Успешные загрузки
    UPLOAD_SUCCESS = 'upload_success'
    
    # Веб-ресурсы
    WEB_RESOURCE_ADD = 'web_resource_add'
    WEB_RESOURCE_CHANGE = 'web_resource_change'
    WEB_RESOURCE_DELETE = 'web_resource_delete'
    WEB_RESOURCE_VIEW = 'web_resource_view'
    WEB_RESOURCE_EXPORT = 'web_resource_export'
    
    # Файловая система
    FILESYSTEM_READ = 'filesystem_read'
    
    # Каталог - открытие элементов
    CATALOG_ITEM_OPEN = 'catalog_item_open'


# Пути к файлам логов аудита
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'audit_log.json')
AUDIT_LOG_DIR = os.path.join(BASE_DIR, 'data', 'audit')


def get_client_ip():
    """
    Получить IP-адрес клиента
    
    Учитывает работу за обратным прокси (nginx, Apache и т.д.)
    Проверяет заголовки X-Forwarded-For, X-Real-IP
    
    Returns:
        str: IP-адрес клиента
    """
    # Проверка заголовков от обратного прокси
    if request:
        # X-Forwarded-For может содержать несколько IP (цепочка прокси)
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            # Первый IP в списке - оригинальный клиент
            ip = x_forwarded_for.split(',')[0].strip()
            return ip
        
        # X-Real-IP (используется nginx)
        x_real_ip = request.headers.get('X-Real-IP')
        if x_real_ip:
            return x_real_ip
        
        # Стандартный remote_addr
        return request.remote_addr or 'unknown'
    
    return 'unknown'


def ensure_audit_dir():
    """Создать директорию для логов аудита если не существует"""
    os.makedirs(AUDIT_LOG_DIR, exist_ok=True)


def get_audit_log_path():
    """
    Получить путь к текущему файлу лога аудита
    
    Использует ежедневную ротацию логов
    
    Returns:
        str: Путь к файлу лога
    """
    ensure_audit_dir()
    today = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(AUDIT_LOG_DIR, f'audit_{today}.json')


def get_yekaterinburg_time():
    """
    Получить текущее время по Екатеринбургу (UTC+5)
    
    Returns:
        datetime: Текущее время в часовом поясе Екатеринбург
    """
    # Получаем текущее UTC время и добавляем 5 часов
    from datetime import timedelta
    utc_now = datetime.utcnow()
    yekaterinburg_time = utc_now + timedelta(seconds=YEKATERINBURG_OFFSET)
    return yekaterinburg_time


def log_audit_event(event_type, object_id, object_type=None, description=None, 
                    additional_data=None, username=None, status=None):
    """
    Записать событие в журнал аудита
    
    Args:
        event_type (str): Тип события (из AuditEventType)
        object_id (str): Идентификатор объекта воздействия
        object_type (str, optional): Тип объекта (resource, file, user, etc.)
        description (str, optional): Описание события
        additional_data (dict, optional): Дополнительные данные
        username (str, optional): Имя пользователя
        status (str|int, optional): Статус события (success, error, initiated, или HTTP статус код)
    
    Returns:
        dict: Созданная запись аудита
    """
    timestamp = get_yekaterinburg_time()
    
    audit_entry = {
        'id': generate_audit_id(),
        'timestamp': timestamp.isoformat(),
        'timestamp_formatted': timestamp.strftime('%d.%m.%Y %H:%M:%S'),
        'event_type': event_type,
        'object_id': object_id,
        'object_type': object_type,
        'ip_address': get_client_ip(),
        'username': username,
        'description': description,
        'status': status,
        'additional_data': additional_data or {}
    }
    
    # Сохраняем в файл
    save_audit_entry(audit_entry)
    
    return audit_entry


def generate_audit_id():
    """
    Сгенерировать уникальный ID для записи аудита
    
    Returns:
        str: Уникальный идентификатор
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    return f'AUDIT_{timestamp}'


def save_audit_entry(entry):
    """
    Сохранить запись аудита в файл
    
    Args:
        entry (dict): Запись для сохранения
    """
    log_file = get_audit_log_path()
    
    # Читаем существующие логи или создаём новую структуру
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except (json.JSONDecodeError, IOError):
            logs = {'entries': []}
    else:
        logs = {'entries': []}
    
    # Добавляем новую запись
    logs['entries'].append(entry)
    
    # Сохраняем обратно в файл
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)


def audit_error(error_type, object_id, description=None, exception=None, additional_data=None, status=None):
    """
    Зафиксировать ошибку в журнале аудита
    
    Args:
        error_type (str): Тип ошибки
        object_id (str): Идентификатор объекта, где произошла ошибка
        description (str, optional): Описание ошибки
        exception (Exception, optional): Объект исключения
        additional_data (dict, optional): Дополнительные данные
        status (str|int, optional): Статус события
    
    Returns:
        dict: Запись аудита
    """
    username = _get_current_user_info()
    
    data = {
        'error_type': error_type,
        'exception_type': type(exception).__name__ if exception else None,
        'exception_message': str(exception) if exception else None,
        **(additional_data or {})
    }
    
    return log_audit_event(
        event_type=AuditEventType.ERROR,
        object_id=object_id,
        object_type='error',
        description=description or f'Ошибка: {error_type}',
        additional_data=data,
        username=username,
        status=status or 'error'
    )


def _get_current_user_info():
    """
    Получить имя текущего пользователя
    
    Работает как внутри Flask-контекста, так и без него.
    Если пользователь не авторизован или контекст недоступен, возвращает None.
    
    Returns:
        str or None: Имя пользователя или None если недоступно
    """
    try:
        from flask import has_request_context
        if not has_request_context():
            return None
        
        from flask_login import current_user
        username = current_user.username if hasattr(current_user, 'username') and current_user.is_authenticated else None
        return username
    except Exception:
        # В случае любой ошибки (например, нет контекста приложения)
        return None


def audit_upload_success(object_id, object_type='item', description=None, additional_data=None, status=None):
    """
    Зафиксировать успешную загрузку элемента
    
    Args:
        object_id (str): Идентификатор загруженного элемента
        object_type (str, optional): Тип элемента
        description (str, optional): Описание
        additional_data (dict, optional): Дополнительные данные
        status (str|int, optional): Статус события
    
    Returns:
        dict: Запись аудита
    """
    username = _get_current_user_info()
    
    return log_audit_event(
        event_type=AuditEventType.UPLOAD_SUCCESS,
        object_id=object_id,
        object_type=object_type,
        description=description or f'Успешная загрузка: {object_id}',
        additional_data=additional_data or {},
        username=username,
        status=status or 'success'
    )


def audit_web_resource(event_type, object_id, object_type='resource', description=None, additional_data=None, status=None):
    """
    Зафиксировать событие с веб-ресурсом
    
    Args:
        event_type (str): Тип события (add, change, delete, view, export)
        object_id (str): Идентификатор ресурса
        object_type (str, optional): Тип ресурса
        description (str, optional): Описание
        additional_data (dict, optional): Дополнительные данные
        status (str|int, optional): Статус события
    
    Returns:
        dict: Запись аудита
    """
    username = _get_current_user_info()
    
    # Маппинг типов событий
    event_type_map = {
        'add': AuditEventType.WEB_RESOURCE_ADD,
        'change': AuditEventType.WEB_RESOURCE_CHANGE,
        'delete': AuditEventType.WEB_RESOURCE_DELETE,
        'view': AuditEventType.WEB_RESOURCE_VIEW,
        'export': AuditEventType.WEB_RESOURCE_EXPORT
    }
    
    audit_event = event_type_map.get(event_type, AuditEventType.WEB_RESOURCE_CHANGE)
    
    return log_audit_event(
        event_type=audit_event,
        object_id=object_id,
        object_type=object_type,
        description=description or f'Операция с ресурсом: {event_type}',
        additional_data=additional_data or {},
        username=username,
        status=status
    )


def audit_filesystem_read(file_path, description=None, additional_data=None, status=None):
    """
    Зафиксировать чтение файла из файловой системы
    
    Args:
        file_path (str): Путь к прочитанному файлу
        description (str, optional): Описание
        additional_data (dict, optional): Дополнительные данные
        status (str|int, optional): Статус события
    
    Returns:
        dict: Запись аудита
    """
    username = _get_current_user_info()
    
    return log_audit_event(
        event_type=AuditEventType.FILESYSTEM_READ,
        object_id=file_path,
        object_type='file',
        description=description or f'Чтение файла: {file_path}',
        additional_data={
            'file_path': file_path,
            **(additional_data or {})
        },
        username=username,
        status=status
    )


def audit_catalog_item_open(item_path, item_name, status_code, item_type='item', description=None, additional_data=None):
    """
    Зафиксировать открытие элемента каталога с указанием статуса
    
    Args:
        item_path (str): Путь элемента каталога
        item_name (str): Имя элемента
        status_code (int): Статус ответа (200 - успех, 404 - не найдено, и т.д.)
        item_type (str, optional): Тип элемента (item, folder, resource)
        description (str, optional): Описание
        additional_data (dict, optional): Дополнительные данные
    
    Returns:
        dict: Запись аудита
    """
    username = _get_current_user_info()
    
    # Определение статуса в текстовом виде
    status_text = 'success' if status_code == 200 else 'error' if status_code >= 400 else 'redirect'
    
    data = {
        'item_path': item_path,
        'item_name': item_name,
        'status_code': status_code,
        'status_text': status_text,
        **(additional_data or {})
    }
    
    return log_audit_event(
        event_type=AuditEventType.CATALOG_ITEM_OPEN,
        object_id=item_path,
        object_type=item_type,
        description=description or f'Открытие элемента каталога: {item_name} (статус: {status_code})',
        additional_data=data,
        username=username,
        status=status_text
    )


def load_audit_logs(date=None, limit=100, offset=0, event_type=None, object_id=None):
    """
    Загрузить записи журнала аудита с фильтрацией
    
    Args:
        date (str, optional): Дата в формате YYYY-MM-DD
        limit (int, optional): Максимальное количество записей
        offset (int, optional): Смещение для пагинации
        event_type (str, optional): Фильтр по типу события
        object_id (str, optional): Фильтр по ID объекта
    
    Returns:
        dict: Результат с записями и общей информацией
    """
    if date is None:
        log_file = get_audit_log_path()
    else:
        log_file = os.path.join(AUDIT_LOG_DIR, f'audit_{date}.json')
    
    if not os.path.exists(log_file):
        return {
            'entries': [],
            'total': 0,
            'limit': limit,
            'offset': offset
        }
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            'entries': [],
            'total': 0,
            'limit': limit,
            'offset': offset
        }
    
    entries = logs.get('entries', [])
    
    # Применяем фильтры
    if event_type:
        entries = [e for e in entries if e.get('event_type') == event_type]
    
    if object_id:
        entries = [e for e in entries if e.get('object_id') == object_id]
    
    total = len(entries)
    
    # Применяем пагинацию
    entries = entries[offset:offset + limit]
    
    # Сортируем по времени (новые сверху)
    entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return {
        'entries': entries,
        'total': total,
        'limit': limit,
        'offset': offset
    }


def clear_audit_logs(date=None):
    """
    Очистить журнал аудита
    
    Args:
        date (str, optional): Дата для очистки. Если None, очищается текущий день.
    
    Returns:
        bool: True если успешно
    """
    if date is None:
        log_file = get_audit_log_path()
    else:
        log_file = os.path.join(AUDIT_LOG_DIR, f'audit_{date}.json')
    
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
            return True
        except OSError:
            return False
    
    return True


def audit_decorator(event_type, object_id_extractor=None):
    """
    Декоратор для автоматического аудита действий
    
    Args:
        event_type (str): Тип события
        object_id_extractor (callable, optional): Функция для извлечения ID объекта из request
    
    Example:
        @audit_decorator('web_resource_add')
        def add_resource():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Выполняем функцию
            result = func(*args, **kwargs)
            
            # Получаем ID объекта
            object_id = None
            if object_id_extractor:
                object_id = object_id_extractor(request, result)
            else:
                # Пытаемся получить из URL или данных
                object_id = request.path
            
            # Логируем успех
            if event_type.startswith('web_resource_'):
                audit_web_resource(event_type.replace('web_resource_', ''), object_id)
            elif event_type == 'upload':
                audit_upload_success(object_id)
            
            return result
        
        return wrapper
    return decorator


# Экспорт всех функций и констант
__all__ = [
    'AuditEventType',
    'AUDIT_LOG_FILE',
    'AUDIT_LOG_DIR',
    'YEKATERINBURG_OFFSET',
    'get_yekaterinburg_time',
    'get_client_ip',
    'log_audit_event',
    'audit_error',
    'audit_upload_success',
    'audit_web_resource',
    'audit_filesystem_read',
    'audit_catalog_item_open',
    'load_audit_logs',
    'clear_audit_logs',
    'audit_decorator',
    '_get_current_user_info'
]
