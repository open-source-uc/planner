#!/bin/bash

# Definir el directorio del repositorio
REPO_DIR=/opt/planner

# Moverse al directorio del repositorio
cd "$REPO_DIR"

# Actualizar la rama main del repositorio
# git fetch origin main
git fetch origin prepare-deploy

# Obtener el hash del commit local y el remoto
LOCAL=$(git rev-parse HEAD)
# REMOTE=$(git rev-parse origin/main)
REMOTE=$(git rev-parse origin/prepare-deploy)

# Si se detectan cambios, ejecutar run_deploy.sh
if [ "$LOCAL" != "$REMOTE" ]; then
    echo "Changes detected. Running deploy script..."
    # git checkout origin/main
    git checkout origin/prepare-deploy
    chmod +x ./run_deploy.sh
    ./run_deploy.sh
else
    # No se detectaron cambios
    # echo "No changes detected. No action needed."
fi
