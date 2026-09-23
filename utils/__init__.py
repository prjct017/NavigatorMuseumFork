"""
Инициализация пакета utils
"""
from .data_utils import (
    ensure_data_dir,
    load_json_file,
    save_json_file,
    get_current_timestamp,
    get_full_timestamp
)

from .parser_utils import (
    extract_items_from_html,
    parse_folder
)

from .auth_utils import (
    User,
    hash_password,
    verify_password,
    create_user,
    admin_required_decorator
)

from .catalog_utils import (
    get_item_path,
    mark_permanent_recursive,
    merge_with_permanent,
    find_item_by_path,
    delete_item_by_path,
    update_item_by_path
)

__all__ = [
    # data_utils
    'ensure_data_dir',
    'load_json_file',
    'save_json_file',
    'get_current_timestamp',
    'get_full_timestamp',
    
    # parser_utils
    'extract_items_from_html',
    'parse_folder',
    
    # auth_utils
    'User',
    'hash_password',
    'verify_password',
    'create_user',
    'admin_required_decorator',
    
    # catalog_utils
    'get_item_path',
    'mark_permanent_recursive',
    'merge_with_permanent',
    'find_item_by_path',
    'delete_item_by_path',
    'update_item_by_path',
]
