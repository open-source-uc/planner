# First, build the dependencies
FROM python:3.11 as requirements-stage

# Set working directory
WORKDIR /tmp

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install Poetry
RUN pip install --no-cache-dir --upgrade poetry

# Copy necessary files for installing dependencies
COPY ./pyproject.toml ./poetry.lock* /tmp/

# Install dependencies
RUN poetry export -f requirements.txt --without-hashes --output requirements.txt

# Second, build the final image
FROM tiangolo/uvicorn-gunicorn:python3.11

# Install system packages
# We use curl for the healthcheck
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential curl

# Install Node 18 (for Prisma)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs \
    build-essential && \
    node --version && \ 
    npm --version

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt

# Install deps from the requirements-stage
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# TODO: copy only the necessary files
# Copy the application code, including config and env files
COPY ./ /app
WORKDIR /app

# Generate the Prisma client
RUN prisma generate

ENV PRE_START_PATH /app/scripts/prestart.sh

# Monitor the app
HEALTHCHECK --start-period=5m CMD curl -f http://localhost:80/health || exit 1
