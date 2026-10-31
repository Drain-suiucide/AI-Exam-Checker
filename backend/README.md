# Backend AI Exam Checker

FastAPI-приложение: каталог конфигураций заданий, OCR-пайплайн (Tesseract / mock), движок оценивания с защитой от галлюцинаций, workflow экспертной проверки.

## Что реализовано

- `GET /health` и `GET /api/v1/health` — health-check (без зависимости от БД);
- `GET /api/v1/exam-configurations` — каталог конфигураций (демо-провайдер);
- конфигурация из окружения через pydantic-settings (`app/config.py`);
- единый формат ошибок (`app/exceptions.py`) и эхо `X-Request-ID`;
- OCR-пайплайн (`app/services/ocr/`): валидация изображений, Tesseract и mock-движки, метрики CER/WER, синтетический генератор датасета;
- движок оценивания (`app/services/evaluation/`): версионированные критерии, пост-валидация ответа LLM (проверка цитат, границ баллов), эскалация спорных случаев;
- workflow экспертной проверки с аудит-трейлом и оптимистичными блокировками.

Известные ограничения (маршруты submissions, RBAC, rate limiting) — в корневом [README.md](../README.md) и [docs/evaluation/qa-report.md](../docs/evaluation/qa-report.md).

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
