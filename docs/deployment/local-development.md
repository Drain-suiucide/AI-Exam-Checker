# Локальный запуск и остановка каркаса (T-005)

Каркас репозитория: FastAPI-бэкенд + Vite/React-фронтенд + PostgreSQL 16 в Docker Compose.
Полноценная проверка ответов **не реализована** (T-006+); работает только health-check.

Требования: Docker 29+ с Compose v5+, Python 3.12+, uv, Node 22+, npm. Проверено на:
Windows 10, Docker 29.8.2 / Compose v5.6.0, Node 26.12.1, npm 11.20.0, uv 0.12.22, Python 3.14 (в `.venv`).

## Запуск через Docker Compose (основной способ)

```powershell
# из корня репозитория
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health        # {"status":"ok"}
curl http://localhost:8080/api/v1/health # {"status":"ok","service":"ai-exam-checker-backend","version":"0.1.0"}
```

- Веб-приложение: http://localhost:8080 (nginx: статика SPA + прокси `/api` → backend).
- Backend: http://localhost:8000, Swagger UI — http://localhost:8000/docs.
- PostgreSQL: localhost:5432, демо-учётные данные `exam_checker / exam_checker_local` (не секреты).

## Остановка

```powershell
docker compose down            # остановить и удалить контейнеры, сеть
docker compose down -v         # то же + удалить volume pgdata (данные БД)
docker compose logs -f backend # логи сервиса
```

## Локальный запуск без Docker (по частям)

### Backend

```powershell
cd backend
uv sync                 # создаёт .venv, ставит зависимости точно из uv.lock
uv run pytest           # тесты
uv run start            # сервер на http://localhost:8000
curl http://localhost:8000/health
```

### Frontend

```powershell
cd frontend
npm ci                  # установка точно из package-lock.json
npm test                # vitest
npm run lint            # eslint
npm run dev             # http://localhost:5173; /api проксируется на :8000
```

## Конфигурация окружения

`backend/.env.example` — шаблон. Скопируйте в `backend/.env` при прямом запуске
без Docker; в compose значения задаются в `docker-compose.yml`. Демонстрационные
значения `OCR_ENGINE=mock`, `LLM_PROVIDER=mock`, `DEMO_MODE=true` указывают, что
адаптеры ещё не реализованы. Реальных ключей и паролей в репозитории нет;
`.env` игнорируется Git (`.gitignore`).

## Проверки запуска (фактические результаты, 2026-10-27)

| Проверка | Команда | Результат |
|---|---|---|
| Установка backend | `uv sync` | OK, 31 пакет из uv.lock |
| Тесты backend | `uv run pytest` | 2 passed |
| Запуск backend | `uv run start` | OK |
| Ответ /health | `curl localhost:8000/health` | `{"status":"ok"}` |
| Установка frontend | `npm ci` | OK, 261+ пакет из lock |
| Сборка frontend | `npm run build` (tsc -b strict + vite) | OK, dist/ собран |
| Тесты frontend | `npm test` | 4 passed |
| Линтер frontend | `npm run lint` | без ошибок |
| compose-конфигурация | `docker compose config --quiet` | OK (exit 0) |
| Сборка образов | `docker compose build backend web` | см. отчёт задачи |
| Запуск compose | `docker compose up -d` | см. отчёт задачи |

## Известные ограничения

- В `/health` нет проверки БД — добавляется в T-006 вместе с сессией SQLAlchemy и миграциями Alembic.
- PostgreSQL в compose не содержит схемы данных: миграций ещё нет.
- `OCR_ENGINE=mock`, `LLM_PROVIDER=mock` — заглушки до реализации адаптеров.
- Docker-образы впервые собираются в среде локальной разработки; кэш `pgdata` создаётся при первом `up`.
