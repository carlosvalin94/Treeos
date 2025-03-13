#!/bin/bash

# Crear la repository copr
echo -e "[copr:copr.fedorainfracloud.org:phracek:PyCharm]\nname=Copr repo for PyCharm owned by phracek\nbaseurl=https://download.copr.fedorainfracloud.org/results/phracek/PyCharm/fedora-\$releasever-\$basearch/\ntype=rpm-md\nskip_if_unavailable=True\ngpgcheck=1\ngpgkey=https://download.copr.fedorainfracloud.org/results/phracek/PyCharm/pubkey.gpg\nrepo_gpgcheck=0\nenabled=1\nenabled_metadata=1" | sudo tee -a /etc/yum.repos.d/phracek-pycharm.repo

# Instalar dependencias
sudo dnf install -y python3-tkinter pycharm-community libXtst xorg-x11-server-Xvfb

# Crear el archivo de inicio para PyCharm
echo -e "[Desktop Entry]\nName=PyCharm (Toolbox)\nComment=IDE for Python Development\nExec=toolbox run --container treeossecure pycharm-community\nIcon=pycharm\nTerminal=false\nType=Application\nCategories=Development;IDE;" | tee ~/.local/share/applications/pycharm-treeossecure.desktop

# Agregar permisos de ejecuci�n
chmod +x ~/.local/share/applications/pycharm-treeossecure.desktop
