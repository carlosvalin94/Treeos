#!/bin/bash
# Script de desinstalaci�n para PyCharm (Toolbox)

# Eliminar el archivo de inicio para PyCharm
DESKTOP_FILE="$HOME/.local/share/applications/pycharm-treeossecure.desktop"
if [ -f "$DESKTOP_FILE" ]; then
  rm "$DESKTOP_FILE"
  echo "Se ha eliminado el acceso directo: $DESKTOP_FILE"
else
  echo "No se encontr� el archivo de acceso directo: $DESKTOP_FILE"
fi

# Desinstalar las dependencias instaladas con dnf
echo "Desinstalando dependencias instaladas con dnf..."
sudo dnf remove -y python3-tkinter pycharm-community libXtst xorg-x11-server-Xvfb

# Eliminar la repository COPR creada
REPO_FILE="/etc/yum.repos.d/phracek-pycharm.repo"
if [ -f "$REPO_FILE" ]; then
  sudo rm "$REPO_FILE"
  echo "Repositorio removido: $REPO_FILE"
else
  echo "No se encontr� el repositorio: $REPO_FILE"
fi

echo "Proceso de desinstalaci�n completado."
