#!/bin/bash
# Script para actualizar el sistema e instalar Visual Studio Code en Fedora

# Actualizar el sistema y refrescar la cach\ufffd de DNF
sudo dnf upgrade --refresh

# Importar la llave GPG de Visual Studio Code para verificar la autenticidad de los paquetes
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc

# Configurar el repositorio de Visual Studio Code
printf "[vscode]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode/\nenabled=1\ngpgcheck=1\nrepo_gpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc\nmetadata_expire=1h" | sudo tee /etc/yum.repos.d/vscode.repo

# Instalar la versi\ufffdn estable de Visual Studio Code
sudo dnf install -y code

# Crear el archivo de acceso directo para Visual Studio Code (modo Toolbox)
echo -e "[Desktop Entry]\nName=Visual Studio Code (Toolbox)\nComment=IDE para desarrollo de c\ufffddigo\nExec=toolbox run --container treeossecure code\nIcon=code\nTerminal=false\nType=Application\nCategories=Development;IDE;" | tee ~/.local/share/applications/vscode-treeossecure.desktop

# Agregar permisos de ejecuci\ufffdn
chmod +x ~/.local/share/applications/vscode-treeossecure.desktop
