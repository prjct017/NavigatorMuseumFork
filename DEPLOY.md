# Как открыть проект с любой точки мира

Этот проект можно развернуть и сделать доступным из любой точки мира несколькими способами:

## 🚀 Быстрый старт

### Вариант 1: Docker (Рекомендуется)

```bash
# Подготовьте переменные окружения
cp .env.example .env
# Затем задайте SECRET_KEY и DEFAULT_ADMIN_PASSWORD в .env

# Запуск через Docker Compose
docker compose up -d

# Приложение будет доступно по адресу: http://localhost:5000
```

### Вариант 2: Прямой запуск Python

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
python app.py

# Приложение будет доступно по адресу: http://0.0.0.0:5000
```

---

## 🌍 Публикация в интернете

### Способ 1: Ngrok (Быстрый временный доступ)

```bash
# Установите ngrok: https://ngrok.com/download
ngrok http 5000
```
После запуска вы получите публичный URL вида `https://xxxx-xxxx.ngrok.io`

### Способ 2: Cloudflare Tunnel (Бесплатно и безопасно)

```bash
# Установите cloudflared
# Запустите туннель
cloudflared tunnel --url http://localhost:5000
```

### Способ 3: Развёртывание на VPS сервере

1. Арендуйте сервер (DigitalOcean, Hetzner, AWS, etc.)
2. Установите Docker и Docker Compose
3. Скопируйте проект на сервер
4. Создайте `.env` из `.env.example` и задайте секреты
5. Запустите: `docker compose up -d`
6. Настройте домен и SSL через Nginx + Let's Encrypt

### Способ 4: Платформы для деплоя

- **Render.com** - бесплатный хостинг для веб-приложений
- **Railway.app** - простой деплой с GitHub
- **Fly.io** - глобальное развёртывание
- **PythonAnywhere** - специализированный Python-хостинг

---

## 🔐 Безопасность при публикации

Перед публикацией в интернете:

1. Задайте случайный `SECRET_KEY` через `.env`
2. Задайте сильный `DEFAULT_ADMIN_PASSWORD` до первого запуска
3. Используйте HTTPS (SSL сертификат)
4. Настройте firewall для ограничения доступа

---

## 📦 Docker команды

```bash
# Запуск контейнера через compose
docker compose up -d

# Остановка контейнера
docker compose down

# Просмотр логов
docker compose logs -f
```

---

## ⚙️ Конфигурация

Для production окружения настройте переменные:

```bash
export FLASK_ENV=production
export SECRET_KEY=ваш-секретный-ключ
export DEFAULT_ADMIN_PASSWORD=ваш-пароль-администратора
```

Или используйте `.env` файл с `docker compose`.
