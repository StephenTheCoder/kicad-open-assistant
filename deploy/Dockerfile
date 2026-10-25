ARG PYTHON_BASE=python:3.11-slim-bookworm@sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf
FROM ${PYTHON_BASE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
COPY requirements-service.lock /app/
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements-service.lock \
    && useradd --uid 10001 --create-home assistant \
    && mkdir /data && chown assistant:assistant /data
COPY src /app/src
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "kicad_open_assistant.service.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "8", "--timeout-keep-alive", "5", "--timeout-graceful-shutdown", "5"]
