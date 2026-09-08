# rubigram membership worker.  Build context: the repository root.
#   docker build -f docker/worker.Dockerfile -t rubigram-worker .

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. the library and the signing helper
COPY pyproject.toml README.md LICENSE ./
COPY rubigram/ ./rubigram/
COPY rubigram_internal/ ./rubigram_internal/
RUN pip install --no-cache-dir -e ".[worker]"

# 2. the worker itself
COPY membership_worker/ ./membership_worker/

ENV PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=membership_worker.project.settings \
    PYTHONUNBUFFERED=1

COPY docker/worker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8001
ENTRYPOINT ["/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8001", "membership_worker.project.asgi:application"]
