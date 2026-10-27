# Backend AI Exam Checker

FastAPI-приложение (каркас T-005). Полноценная проверка ответов — задача T-006+.

## Что реализовано

- `GET /health` и `GET /api/v1/health` — health-check (без зависимости от БД);
- конфигурация из окружения через pydantic-settings (`app/config.py`);
- единый формат ошибок (`app/exceptions.py`) и эхо `X-Request-ID`.

## Локальный запуск

```bash
uv sync                 # создание .venv и установка зависимостей из uv.lock
uv run pytest           # тесты
uv run start            # сервер на http://localhost:8000
```

Проверка: `curl http://localhost:8000/health` → `{"status":"ok"}`.

## Docker

```bash
docker compose build backend
docker compose up backend   # из корня репозитория; БД подключается сервисом db
```

Подробные команды и остановка — `docs/deployment/local-development.md` в корне репозитория.

