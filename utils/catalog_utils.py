"""Утилиты для работы с каталогом и постоянными элементами"""


def get_item_path(item, parent_path=""):
    """Получить полный путь элемента"""
    return f"{parent_path}/{item['name']}" if parent_path else item['name']


def mark_permanent_recursive(items, permanent_paths, parent_path=""):
    """Рекурсивно отметить постоянные элементы"""
    for item in items:
        current_path = get_item_path(item, parent_path)
        if current_path in permanent_paths:
            item['permanent'] = True
        if 'children' in item and item['children']:
            mark_permanent_recursive(item['children'], permanent_paths, current_path)


def merge_with_permanent(new_data, existing_catalog, permanent_paths, parent_path=""):
    """
    Объединяет новые данные парсера с существующим каталогом.
    
    Постоянные элементы сохраняются полностью со всеми свойствами.
    Для непостоянных элементов сохраняются пользовательские свойства (icon).
    Свойство 'icon' никогда не перезаписывается данными из парсера.
    """
    result = []
    existing_by_name_lower = {item['name'].lower(): item for item in existing_catalog}
    
    for new_item in new_data:
        current_path = get_item_path(new_item, parent_path)
        new_item_name_lower = new_item['name'].lower()
        existing_item = existing_by_name_lower.get(new_item_name_lower)
        
        if current_path in permanent_paths and existing_item:
            merged_item = existing_item.copy()
            if merged_item.get('children') is not None and new_item.get('children') is not None:
                merged_item['children'] = _merge_children(
                    new_item['children'], existing_item.get('children', []),
                    permanent_paths, current_path
                )
            result.append(merged_item)
        elif existing_item:
            merged_item = existing_item.copy()
            has_custom_icon = existing_item.get('icon') and existing_item.get('icon').strip()
            
            # Сохраняем флаг isEmpty из новых данных парсера
            if 'isEmpty' in new_item:
                merged_item['isEmpty'] = new_item['isEmpty']
            
            if 'children' in new_item:
                if new_item['children'] is not None:
                    merged_item['children'] = _merge_children(
                        new_item['children'], existing_item.get('children', []),
                        permanent_paths, current_path
                    )
                    # Пересчитываем isEmpty после слияния children
                    has_children = len(merged_item.get('children', [])) > 0
                    has_url = merged_item.get('url') and str(merged_item['url']).strip()
                    merged_item['isEmpty'] = not has_children and not has_url
                else:
                    merged_item['children'] = None
            
            if not has_custom_icon:
                if 'url' in new_item:
                    merged_item['url'] = new_item['url']
                if 'modified' in new_item:
                    merged_item['modified'] = new_item['modified']
            
            result.append(merged_item)
        else:
            if 'children' in new_item and new_item['children'] is not None:
                new_item['children'] = _merge_children(
                    new_item['children'],
                    existing_by_name_lower.get(new_item_name_lower, {}).get('children', []),
                    permanent_paths, current_path
                )
            result.append(new_item)
    
    # Добавить постоянные элементы, которых нет в новых данных
    result_names_lower = {item['name'].lower() for item in result}
    for name, existing_item in existing_by_name_lower.items():
        current_path = get_item_path(existing_item, parent_path)
        if current_path in permanent_paths and name not in result_names_lower:
            result.append(existing_item)
    
    return result


def _merge_children(new_children, existing_children, permanent_paths, parent_path):
    """
    Рекурсивно объединяет children, сохраняя все существующие элементы.
    Пользовательские свойства (icon) не перезаписываются.
    """
    result = [item.copy() for item in existing_children]
    existing_names_lower = {item['name'].lower(): item for item in existing_children}
    
    for new_item in new_children:
        current_path = get_item_path(new_item, parent_path)
        new_item_name_lower = new_item['name'].lower()
        
        if new_item_name_lower in existing_names_lower:
            for i, result_item in enumerate(result):
                if result_item['name'].lower() == new_item_name_lower:
                    saved_icon = result_item.get('icon')
                    saved_permanent = result_item.get('permanent')
                    has_custom_icon = saved_icon and saved_icon.strip()
                    
                    if new_item.get('children') is not None:
                        result[i]['children'] = _merge_children(
                            new_item['children'], result_item.get('children', []),
                            permanent_paths, current_path
                        )
                        # Пересчитываем isEmpty после слияния children
                        has_children_flag = len(result[i].get('children', [])) > 0
                        has_url_flag = result[i].get('url') and str(result[i]['url']).strip()
                        result[i]['isEmpty'] = not has_children_flag and not has_url_flag
                    
                    # Сохраняем флаг isEmpty из новых данных, если он есть
                    if 'isEmpty' in new_item and 'children' not in new_item:
                        result[i]['isEmpty'] = new_item['isEmpty']
                    
                    if not has_custom_icon:
                        if 'url' in new_item:
                            result[i]['url'] = new_item['url']
                        if 'modified' in new_item:
                            result[i]['modified'] = new_item['modified']
                    
                    if saved_icon is not None:
                        result[i]['icon'] = saved_icon
                    if saved_permanent is not None:
                        result[i]['permanent'] = saved_permanent
                    break
        else:
            new_item_copy = new_item.copy()
            if new_item.get('children') is not None:
                new_item_copy['children'] = _merge_children(
                    new_item['children'], [], permanent_paths, current_path
                )
            result.append(new_item_copy)
    
    return result


def find_item_by_path(items, target_path, current_path=""):
    """Найти элемент по пути"""
    for item in items:
        item_path = get_item_path(item, current_path)
        if item_path == target_path:
            return item
        if 'children' in item and item['children']:
            found = find_item_by_path(item['children'], target_path, item_path)
            if found:
                return found
    return None


def delete_item_by_path(items, target_path, current_path=""):
    """Удалить элемент по пути"""
    for i, item in enumerate(items):
        item_path = get_item_path(item, current_path)
        if item_path == target_path:
            items.pop(i)
            return True
        if 'children' in item and item['children']:
            if delete_item_by_path(item['children'], target_path, item_path):
                return True
    return False


def update_item_by_path(items, target_path, updates, current_path=""):
    """Обновить элемент по пути"""
    for item in items:
        item_path = get_item_path(item, current_path)
        if item_path == target_path:
            item.update(updates)
            return True
        if 'children' in item and item['children']:
            if update_item_by_path(item['children'], target_path, updates, item_path):
                return True
    return False
