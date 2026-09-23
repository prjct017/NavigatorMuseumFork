"""Утилиты для HTTP-ответов приложения."""


STATIC_MIME_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".html": "text/html; charset=utf-8",
}


def add_static_response_headers(response, request_path):
    """
    Добавляет CORS-заголовки и корректные MIME-типы для статических файлов.

    Args:
        response: Flask response object.
        request_path (str): Путь текущего HTTP-запроса.

    Returns:
        Response: Обновлённый Flask response object.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRFToken"
    response.headers["Access-Control-Allow-Credentials"] = "true"

    content_type = response.headers.get("Content-Type", "")
    if content_type.startswith("text/plain") or not content_type:
        for extension, mime_type in STATIC_MIME_TYPES.items():
            if request_path.endswith(extension):
                response.headers["Content-Type"] = mime_type
                break

    return response
