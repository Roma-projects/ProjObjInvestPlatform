# syntax=docker/dockerfile:1.7
# Собирает контейнер Parsers; данные реестров сохраняются в отдельном Docker volume.
FROM python:3.11-slim
WORKDIR /app
COPY parsers/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*
COPY parsers/app ./app
COPY parsers/entrypoint.sh /entrypoint.sh
RUN groupadd --system --gid 10001 parsers \
    && useradd --system --uid 10001 --gid parsers --create-home parsers \
    && mkdir -p /parsers_storage \
    && chown -R 10001:10001 /app /parsers_storage
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["sh", "/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
