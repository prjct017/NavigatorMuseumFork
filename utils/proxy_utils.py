"""Утилиты для работы приложения за обратным прокси."""

from werkzeug.middleware.proxy_fix import ProxyFix


class PathPrefixMiddleware:
    """
    Middleware для удаления префикса пути перед обработкой запроса Flask.

    Args:
        app: WSGI-приложение Flask.
        prefix (str): Внешний URL-префикс приложения.
    """

    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix.rstrip("/")

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        script_name = environ.get("SCRIPT_NAME", "")

        if not script_name and path.startswith(self.prefix):
            environ["PATH_INFO"] = path[len(self.prefix):] or "/"
            environ["SCRIPT_NAME"] = self.prefix

        return self.app(environ, start_response)


def configure_proxy_support(app, prefix):
    """
    Настраивает поддержку reverse proxy и внешнего URL-префикса.

    Args:
        app: Экземпляр Flask-приложения.
        prefix (str): Внешний URL-префикс приложения.

    Returns:
        Flask: Тот же экземпляр приложения с обновлённым WSGI stack.
    """
    app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)
    app.wsgi_app = PathPrefixMiddleware(app.wsgi_app, prefix)
    app.config["APPLICATION_ROOT"] = prefix
    return app
