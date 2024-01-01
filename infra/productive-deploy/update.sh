#!/bin/bash

# Definir el directorio del repositorio
REPO_DIR=/opt/planner

# Moverse al directorio del repositorio
cd "$REPO_DIR"

# Actualizar la rama main del repositorio
git fetch origin main

# Obtener el hash del commit local y el remoto
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

# Si se detectan cambios, ejecutar run_deploy.sh
if [ "$LOCAL" != "$REMOTE" ]; then
    echo "Changes detected. Running deploy script..."
    git checkout origin/main
    ./run_deploy.sh
else
    echo "No changes detected. No action needed."
fi
