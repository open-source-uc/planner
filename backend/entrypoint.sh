#!/bin/bash

# Set working directory
cd /code

# Apply prisma migrations
prisma migrate deploy

# Start FastAPI server using Gunicorn with Uvicorn workers
gunicorn app.main:app
