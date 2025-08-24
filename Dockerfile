FROM python:3.13.5-alpine3.22
LABEL authors="Beshence"

RUN apk add --no-cache curl git

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Use the system Python environment
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"

COPY ./pyproject.toml /app/pyproject.toml

RUN uv sync

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 443

# Запускаем бота
CMD ["python", "start.py"]