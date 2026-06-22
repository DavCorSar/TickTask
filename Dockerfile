# Backend image. The same image runs the Django API, the Celery worker and
# beat, and the Telegram polling bot — the compose file overrides the command
# per service.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

# Install dependencies first (cached unless pyproject/uv.lock change).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

CMD ["uv", "run", "python", "ticktask/manage.py", "runserver", "0.0.0.0:8000"]
