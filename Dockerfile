# syntax=docker/dockerfile:1.6

FROM python:3.12-slim AS builder
WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m pip install --upgrade pip setuptools wheel

COPY pyproject.toml README.md LICENSE alembic.ini ./
COPY src ./src
COPY migrations ./migrations

RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir /wheels .

FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN adduser --disabled-password --gecos "" --uid 10001 appuser

COPY --from=builder /wheels /wheels
RUN python -m pip install /wheels/tg_wiki-*.whl \
    && rm -rf /wheels

COPY alembic.ini ./
COPY migrations ./migrations

USER appuser

CMD ["tg-wiki"]