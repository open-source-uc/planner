#!/bin/bash


# Notas sobre este archivo:
# 1. Este archivo solamente debe ser usado para buscar cambios y actualizar automáticamente la máquina de producción del planner.
# 2. NO se debe usar este archivo en ambientes de desarrollo.
# 3. Ningún cambio a este archivo se verá reflejado en la máquina de producción de forma automática. Para actualizarlo, se debe solicitar el administrador de la máquina que vuelva a copiar el archivo hacia la ubicación en que se utiliza.

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
    git restore .
    git checkout origin/main
    chmod +x ./run_deploy.sh
    ./run_deploy.sh
fi
