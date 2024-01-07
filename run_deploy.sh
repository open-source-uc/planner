#!/bin/bash

# Notas sobre este archivo:
# 1. Este archivo solamente debe ser usado para generar despliegues del planner en la máquina de producción.
# 2. NO se debe usar este archivo en ambientes de desarrollo.
# 3. Este archivo puede ser modificado, y debería actualizarse automáticamente en la máquina de producción.

# Instalar Ansible si no está presente
if ! command -v ansible >/dev/null; then
    echo "Ansible no está instalado. Instalando Ansible..."
    sudo dnf install epel-release
    sudo dnf install ansible -y
fi

# Instalar el módulo community.docker si no está presente
if ! ansible-galaxy collection list | grep -q 'community.docker'; then
    echo "Instalando el módulo community.docker para Ansible..."
    ansible-galaxy collection install community.docker
fi

# Definir el directorio del playbook
PLAYBOOK_DIR=/opt/planner/infra

# Ejecutar el playbook de Ansible
echo "Ejecutando el playbook de Ansible..."
ansible-playbook "$PLAYBOOK_DIR/playbook.yml"
