#!/bin/bash
# Script de desinstalaci�n para Anaconda (Toolbox)

# Eliminar el acceso directo de Anaconda
DESKTOP_FILE="$HOME/.local/share/applications/anaconda-treeossecure.desktop"
if [ -f "$DESKTOP_FILE" ]; then
  rm "$DESKTOP_FILE"
  echo "Se ha eliminado el acceso directo: $DESKTOP_FILE"
else
  echo "No se encontr� el archivo de acceso directo: $DESKTOP_FILE"
fi

# Eliminar el entorno conda 'basenv'
echo "Eliminando el entorno conda 'basenv'..."
conda env remove -n basenv

# Desinstalar las dependencias instaladas con dnf
echo "Desinstalando dependencias instaladas con dnf..."
sudo dnf remove -y conda qt5-qtbase qt5-qtbase-gui xcb-util xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil pciutils-libs libXrandr alsa-lib.x86_64 libXdamage libXtst
echo "Proceso de desinstalaci�n completado."
