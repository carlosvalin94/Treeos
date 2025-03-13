#!/bin/bash

# Instalar dependencias
sudo dnf install -y conda

conda create -n env1 anaconda-navigator

sudo dnf install qt5-qtbase qt5-qtbase-gui xcb-util xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil

# Crear el archivo de acceso directo para Anaconda (modo Toolbox)
echo -e "[Desktop Entry]\nName=Anaconda (Toolbox)\nComment=IDE para desarrollo de c�digo\nExec=toolbox run --container treeossecure conda anaconda-navigator\nIcon=code\nTerminal=false\nType=Application\nCategories=Development;IDE;" | tee ~/.local/share/applications/anaconda-treeossecure.desktop

# Agregar permisos de ejecuci\ufffdn
chmod +x ~/.local/share/applications/anaconda-treeossecure.desktop
