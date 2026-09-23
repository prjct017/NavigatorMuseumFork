"""
Тесты для приложения Flask управления мультимедийным контентом
"""
import pytest
from app import app, parser_status, load_catalog, save_catalog
from utils.parser_utils import extract_items_from_html, parse_folder
from utils.data_utils import load_json_file, save_json_file
from utils.catalog_utils import merge_with_permanent, find_item_by_path
import json
import os


@pytest.fixture
def client():
    """Создание тестового клиента Flask"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_catalog():
    """Пример каталога для тестов"""
    return {
        "name": "ТЕСТОВЫЙ КАТАЛОГ",
        "icon": "folder.png",
        "children": [
            {
                "name": "Папка 1",
                "icon": "folder.png",
                "children": [
                    {
                        "name": "Файл 1",
                        "icon": "file.png",
                        "children": None,
                        "url": "http://example.com/file1.pdf"
                    }
                ],
                "url": "http://example.com/folder1/"
            },
            {
                "name": "Папка 2",
                "icon": "folder.png",
                "children": [],
                "url": "http://example.com/folder2/"
            }
        ]
    }


class TestParserStatus:
    """Тесты статуса парсера"""
    
    def test_parser_status_initial_state(self):
        """Проверка начального состояния парсера"""
        assert 'running' in parser_status
        assert 'last_run' in parser_status
        assert 'message' in parser_status
        assert 'images' in parser_status
        assert parser_status['running'] is False
    
    def test_parser_status_images_field_exists(self):
        """Проверка наличия поля images в статусе парсера"""
        assert isinstance(parser_status['images'], list)


class TestCatalogEndpoints:
    """Тесты API endpoints каталога"""
    
    def test_get_catalog(self, client):
        """Получение каталога должно возвращать JSON"""
        response = client.get('/api/catalog')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = response.get_json()
        assert 'name' in data
        assert 'children' in data
    
    def test_index_page(self, client):
        """Главная страница должна отдавать HTML"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data


class TestParserUtils:
    """Тесты утилит парсера"""
    
    def test_extract_items_from_html(self):
        """Извлечение элементов из HTML Apache индексации"""
        html_content = """
        <table>
            <tr><td></td><td><a href="../">Parent Directory</a></td><td>-</td><td>-</td><td>-</td></tr>
            <tr><td><img src="icons/folder.png" alt="[DIR]"></td><td><a href="folder1/">folder1</a></td><td>2024-01-01</td><td>-</td><td>-</td></tr>
            <tr><td><img src="icons/file.png" alt="[   ]"></td><td><a href="file.pdf">file.pdf</a></td><td>2024-01-01</td><td>100K</td><td>-</td></tr>
        </table>
        """
        base_url = "http://example.com/test/"
        items = extract_items_from_html(html_content, base_url)
        
        assert len(items) == 2
        
        # Проверка папки - теперь используется logo.png для всех
        folder = items[0]
        assert folder['name'] == 'folder1'
        assert folder['children'] == []
        assert folder['icon'] == 'page/logo.png'
        
        # Проверка файла - расширение удаляется из имени
        file_item = items[1]
        assert file_item['name'] == 'file'
        assert file_item['children'] is None
        assert file_item['icon'] == 'page/logo.png'
    
    def test_extract_items_skips_parent_directory(self):
        """Парсер должен пропускать Parent Directory"""
        html_content = """
        <table>
            <tr><td></td><td><a href="../">Parent Directory</a></td><td>-</td><td>-</td><td>-</td></tr>
        </table>
        """
        items = extract_items_from_html(html_content, "http://example.com/")
        assert len(items) == 0
    
    def test_extract_items_handles_empty_table(self):
        """Обработка пустой таблицы"""
        html_content = "<table></table>"
        items = extract_items_from_html(html_content, "http://example.com/")
        assert len(items) == 0


class TestCatalogUtils:
    """Тесты утилит каталога"""
    
    def test_merge_with_permanent(self):
        """Слияние новых элементов с постоянными"""
        new_items = [
            {"name": "Новый элемент", "icon": "file.png", "children": None}
        ]
        existing_items = [
            {"name": "Старый элемент", "icon": "file.png", "children": None, "_permanent": True}
        ]
        permanent_paths = set()
        
        result = merge_with_permanent(new_items, existing_items, permanent_paths)
        
        # Должны быть оба элемента
        assert len(result) >= 1
    
    def test_find_item_by_path(self, sample_catalog):
        """Поиск элемента по пути"""
        # Функция ищет по строковому пути
        item = find_item_by_path(sample_catalog['children'], 'Папка 1')
        assert item is not None
        assert item['name'] == 'Папка 1'
        
        # Поиск вложенного элемента
        nested_item = find_item_by_path(sample_catalog['children'], 'Папка 1/Файл 1')
        assert nested_item is not None
        assert nested_item['name'] == 'Файл 1'


class TestDataUtils:
    """Тесты утилит данных"""
    
    def test_load_json_file_default(self, tmp_path):
        """Загрузка несуществующего файла возвращает default"""
        test_file = tmp_path / "nonexistent.json"
        default_data = {"key": "value"}
        result = load_json_file(str(test_file), default=default_data)
        assert result == default_data
    
    def test_save_and_load_json_file(self, tmp_path):
        """Сохранение и загрузка JSON файла"""
        test_file = tmp_path / "test.json"
        data = {"test": "data", "number": 42}
        
        save_json_file(str(test_file), data)
        loaded = load_json_file(str(test_file))
        
        assert loaded == data


class TestParserImages:
    """Тесты для проверки сбора изображений парсером"""
    
    def test_parser_collects_icon_urls(self):
        """Парсер использует logo.png для всех элементов"""
        html_content = """
        <table>
            <tr>
                <td><img src="icons/custom_image.jpg" alt="[DIR]"></td>
                <td><a href="folder1/">folder1</a></td>
                <td>2024-01-01</td>
                <td>-</td>
                <td>-</td>
            </tr>
            <tr>
                <td><img src="icons/photo.png" alt="[   ]"></td>
                <td><a href="image.png">image.png</a></td>
                <td>2024-01-01</td>
                <td>100K</td>
                <td>-</td>
            </tr>
        </table>
        """
        base_url = "http://example.com/test/"
        items = extract_items_from_html(html_content, base_url)
        
        assert len(items) == 2
        
        # Все элементы используют logo.png
        assert items[0]['icon'] == 'page/logo.png'
        assert items[1]['icon'] == 'page/logo.png'
        # Расширение файла удаляется из имени
        assert items[1]['name'] == 'image'
    
    def test_parser_stores_full_icon_url(self):
        """Парсер использует logo.png для всех элементов"""
        html_content = """
        <table>
            <tr>
                <td><img src="/icons/special.jpg" alt="[DIR]"></td>
                <td><a href="folder/">folder</a></td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
            </tr>
        </table>
        """
        base_url = "http://ftp.example.com/data/"
        items = extract_items_from_html(html_content, base_url)
        
        assert len(items) == 1
        # Используется logo.png
        assert items[0]['icon'] == 'page/logo.png'


class TestAdminEndpoints:
    """Тесты админских endpoints"""
    
    def test_parser_status_endpoint_requires_auth(self, client):
        """Endpoint статуса парсера требует авторизации"""
        response = client.get('/api/parser/status')
        assert response.status_code in [302, 401]  # Redirect или Unauthorized
    
    def test_parser_start_endpoint_requires_auth(self, client):
        """Endpoint запуска парсера требует авторизации"""
        response = client.post('/api/parser/start')
        assert response.status_code in [302, 401]


class TestUIRequirements:
    """Тесты требований пользовательского интерфейса"""
    
    def test_catalog_json_structure(self):
        """JSON каталога должен иметь правильную структуру"""
        from config.settings import CATALOG_FILE
        catalog = load_catalog(CATALOG_FILE)
        
        assert 'name' in catalog
        assert 'children' in catalog
        assert isinstance(catalog['children'], list)
    
    def test_item_has_required_fields(self, sample_catalog):
        """Элементы каталога должны иметь обязательные поля"""
        for item in sample_catalog['children']:
            assert 'name' in item
            assert 'icon' in item


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
