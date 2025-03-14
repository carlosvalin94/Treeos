#!/bin/bash

# Instalar dependencias
sudo dnf install -y conda

sudo dnf install -y qt5-qtbase qt5-qtbase-gui xcb-util xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil pciutils-libs libXrandr alsa-lib.x86_64 libXdamage libXtst
conda config --set channel_priority strict
conda config --append channels defaults
conda create -n basenv -c default anaconda-navigator

# Crear el archivo de acceso directo para Anaconda (modo Toolbox)
# Crear el archivo de inicio para Anaconda
echo -e "[Desktop Entry]\nName=Anaconda (Toolbox)\nComment=IDE para desarrollo de c�digo\nExec=toolbox run --container treeossecure conda run -n basenv anaconda-navigator\nIcon=anaconda\nTerminal=false\nType=Application\nCategories=Development;IDE;" | tee ~/.local/share/applications/anaconda-treeossecure.desktop

# Agregar permisos de ejecuci\ufffdn
chmod +x ~/.local/share/applications/anaconda-treeossecure.desktop
