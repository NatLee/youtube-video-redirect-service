ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
COPY templates templates

# `docker build --target test .` runs the test suite in this same environment.
FROM base AS test
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY tests tests
RUN python -m pytest -q

# The default target: the web app.
FROM base AS app
RUN useradd --create-home --uid 10001 app
USER app
# gunicorn listens on 0.0.0.0:$PORT when PORT is set; main.py reads the same variable.
ENV PORT=5000
EXPOSE 5000
CMD ["gunicorn", "--workers", "2", "--threads", "4", "--access-logfile", "-", "main:app"]
