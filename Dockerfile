FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY prompts ./prompts
COPY data ./data
COPY scripts ./scripts

RUN pip install --upgrade pip && pip install .

CMD ["uvicorn", "accountant_bot.app.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
