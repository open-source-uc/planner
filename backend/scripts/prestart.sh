#!/bin/bash
# This script is used as a prelaunch script when running in production

# Set working directory
cd /app

# Apply prisma migrations
prisma migrate deploy

# Run the startup script
python ./scripts/startup.py