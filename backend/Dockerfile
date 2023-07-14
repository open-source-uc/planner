# First, build the dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Why use venv? https://pmac.io/2019/02/multi-stage-dockerfile-and-python-virtualenv/
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir --upgrade poetry

# Create and activate a virtual environment
RUN python -m venv $VIRTUAL_ENV

# Set working directory
WORKDIR /tmp

# Copy necessary files for installing dependencies
COPY ./pyproject.toml ./poetry.lock* /tmp/

# Install dependencies
RUN poetry export -f requirements.txt --without-hashes | pip install --no-cache-dir -r /dev/stdin

# Copy the `.env` file
COPY ./.env /tmp/.env

# Copy the rest of the application code
COPY . .

# Build code and install package
RUN poetry build && pip install --no-cache-dir dist/*.whl

# Second, build the final image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Prisma CLI
RUN curl -L https://install.prisma.io/cli/ -sSL | bash

# Set working directory
WORKDIR /code

# Copy the virtual environment and entrypoint script from the builder
COPY --from=builder /venv /venv
COPY --from=builder /tmp/entrypoint.sh /entrypoint.sh

# Copy Prisma files and generate client
COPY --from=builder /tmp/prisma /code/prisma
RUN prisma generate

# Copy the .env file and app code from the builder
COPY --from=builder /tmp/.env /code/.env
COPY --from=builder /tmp/app /code/app

# Setup entrypoint
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]

# Expose the necessary port
EXPOSE 8000

# Setup healthcheck
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1