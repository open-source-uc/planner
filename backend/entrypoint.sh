#!/bin/bash

# Set working directory
cd /code

# Apply prisma migrations
prisma migrate deploy

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000
