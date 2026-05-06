FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY shared ./shared
COPY bot ./bot
COPY backend ./backend
COPY worker ./worker
COPY alembic ./alembic
COPY prompts ./prompts
COPY data ./data
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

CMD ["python", "-m", "backend.entrypoint"]
