FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b AS dependencies

WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then \
        export PIP_CERT=/run/secrets/build_ca SSL_CERT_FILE=/run/secrets/build_ca; \
    fi \
    && python -m pip install --no-cache-dir uv==0.13.9 \
    && uv sync --locked --no-dev

FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/visitors.db
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && install -d -o app -g app /data
COPY --from=dependencies /app/.venv /app/.venv
COPY app/ app/
RUN chmod -R a+rX /app/app

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=2).close()"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
