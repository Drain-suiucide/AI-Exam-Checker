# Запечатлённая сборка backend (T-005): версии точно из uv.lock, без секретов.
# Сборка: docker build -t ai-exam-checker-backend ./backend
FROM python:3.12.10-slim-bookworm AS builder

RUN pip install --no-cache-dir uv==0.12.22
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
# Зависимости и пакет ставятся точно из lock-файла (--frozen).
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
RUN uv sync --frozen --no-dev

# --- runtime: только venv и код, без кэшей сборки ---
FROM python:3.12.10-slim-bookworm AS runtime

# Непривилегированный пользователь (ARCHITECTURE §10).
RUN groupadd --gid 1000 appgroup && useradd --uid 1000 --gid appgroup --create-home appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/app ./app

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

EXPOSE 8000

USER appuser

# Docker HEALTHCHECK по короткому пути /health.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

