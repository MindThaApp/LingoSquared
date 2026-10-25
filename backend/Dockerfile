# Multi-stage. `docker compose build` (no target) builds the LAST stage, `dev`,
# exactly as before: requirements-dev.txt (pytest), root, source bind-mounted
# over /app by docker-compose.yml. docker-compose.prod.yml builds `prod`:
# runtime requirements only, code baked in, non-root, healthcheck.

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS prod
# Match the host user that owns the bind-mounted media_assets/ and
# feedback_uploads/ dirs (`id -u` on the server); override with --build-arg.
ARG APP_UID=1000
ENV HF_HOME=/home/app/.cache/huggingface
RUN useradd --create-home --uid ${APP_UID} app \
    && mkdir -p /app/feedback_uploads /app/media_assets "$HF_HOME" \
    && chown -R app:app /app /home/app
COPY --chown=app:app . .
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS dev
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
