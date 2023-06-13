#!/bin/bash

# Set working directory
cd /code

# Load environment variables from .env file
set -o allexport
source .env
set +o allexport

# Apply prisma migrations
prisma migrate deploy

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000
