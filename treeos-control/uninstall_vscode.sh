#!/bin/bash
# Script de desinstalaci�n para Visual Studio Code (Toolbox)

# Eliminar el archivo de acceso directo para Visual Studio Code
DESKTOP_FILE="$HOME/.local/share/applications/vscode-treeossecure.desktop"
if [ -f "$DESKTOP_FILE" ]; then
  rm "$DESKTOP_FILE"
  echo "Se ha eliminado el acceso directo: $DESKTOP_FILE"
else
  echo "No se encontr� el archivo de acceso directo: $DESKTOP_FILE"
fi

# Desinstalar Visual Studio Code
echo "Desinstalando Visual Studio Code..."
sudo dnf remove -y code

# Eliminar el repositorio configurado para Visual Studio Code
REPO_FILE="/etc/yum.repos.d/vscode.repo"
if [ -f "$REPO_FILE" ]; then
  sudo rm "$REPO_FILE"
  echo "Repositorio removido: $REPO_FILE"
else
  echo "No se encontr� el repositorio: $REPO_FILE"
fi

# Nota: La llave GPG importada para Microsoft no se elimina autom�ticamente.
echo "Proceso de desinstalaci�n completado."
