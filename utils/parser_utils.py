"""Утилиты для парсинга FTP-каталога"""
import requests
import urllib3
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# Подавление SSL-предупреждений при использовании verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Задержка между запросами к FTP-серверу (в секундах) для избежания 429 ошибки
REQUEST_DELAY = 2.0  # 2 секунды между запросами


def extract_items_from_html(html_content, base_url):
    """Извлечь элементы каталога из HTML страницы FTP"""
    soup = BeautifulSoup(html_content, 'html.parser')
    items = []
    
    table = soup.find('table')
    if not table:
        return items
    
    rows = table.find_all('tr')
    
    for i, row in enumerate(rows):
        cells = row.find_all('td')
        if len(cells) < 5:
            continue
        
        link = cells[1].find('a')
        if not link:
            continue
        
        name_text = link.get_text(strip=True)
        if name_text == 'Parent Directory':
            continue
        
        href = link.get('href', '')
        modified = cells[2].get_text(strip=True) if cells[2] else None
        
        img = cells[0].find('img')
        is_folder = img and '[DIR]' in img.get('alt', '')
        
        full_url = urljoin(base_url, href)
        
        if is_folder:
            # Папка: считаем пустой по умолчанию (будет обновлено при рекурсивном парсинге)
            is_empty = True
            
            items.append({
                'name': name_text.rstrip('/'),  # Убираем слэш в конце имени
                'icon': 'page/logo.png',
                'children': [],
                'url': full_url,  # URL сохраняем как есть (декодируется при записи в JSON)
                'modified': modified,
                'isEmpty': is_empty
            })
        else:
            # Файл: убираем расширение из имени
            name_without_ext = name_text
            if '.' in name_without_ext:
                name_without_ext = name_without_ext.rsplit('.', 1)[0]
            
            # Проверяем, есть ли URL
            is_empty = not full_url or full_url.strip() == ''
            
            items.append({
                'name': name_without_ext,
                'icon': 'page/logo.png',
                'children': None,
                'url': full_url if not is_empty else None,
                'modified': modified,
                'isEmpty': is_empty
            })
    
    return items


def parse_folder(url, visited=None, depth=0, max_depth=10, timeout=10, max_workers=5):
    """
    Парсинг FTP-каталога с многопоточностью
    
    Args:
        url: URL для парсинга
        visited: множество посещённых URL
        depth: текущая глубина рекурсии
        max_depth: максимальная глубина парсинга
        timeout: таймаут запроса в секундах
        max_workers: количество потоков для параллельного парсинга
    
    Returns:
        list: список элементов каталога
    """
    if visited is None:
        visited = set()
    
    if depth > max_depth:
        return []
    
    if url in visited:
        return []
    
    visited.add(url)
    
    try:
        # Добавляем задержку перед запросом для избежания 429 ошибки
        time.sleep(REQUEST_DELAY)
        
        try:
            response = requests.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            
        except requests.exceptions.Timeout:
            raise
        except requests.exceptions.ConnectionError:
            raise
        except requests.exceptions.RequestException:
            raise
        
        items = extract_items_from_html(response.text, url)
        
        folders_to_parse = [item for item in items if item['children'] is not None and item['url']]
        
        if folders_to_parse and depth < max_depth:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_item = {
                    executor.submit(_parse_folder_recursive, item['url'], visited, depth + 1, max_depth, timeout): item
                    for item in folders_to_parse
                }
                
                for future in as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        result = future.result()
                        item['children'] = result
                        # Обновляем флаг isEmpty: папка пустая, если нет детей И нет URL
                        has_children = len(result) > 0
                        has_url = item.get('url') and item['url'].strip()
                        item['isEmpty'] = not has_children and not has_url
                    except Exception:
                        item['children'] = []
                        item['isEmpty'] = True
        else:
            # Обновляем isEmpty для папок, которые не были распаршены
            for item in items:
                if item.get('children') is not None:  # Это папка
                    has_children = len(item.get('children', [])) > 0
                    has_url = item.get('url') and item['url'].strip()
                    item['isEmpty'] = not has_children and not has_url
        
        return items
        
    except Exception:
        return []


def _parse_folder_recursive(url, visited, depth, max_depth, timeout):
    """Вспомогательная функция для рекурсивного парсинга"""
    return parse_folder(url, visited, depth, max_depth, timeout)
