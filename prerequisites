#!/bin/sh

# Instala los paquetes necesarios
rpm-ostree install steam-devices openrgb-udev-rules gnome-shell-extension-blur-my-shell gnome-shell-extension-dash-to-panel gnome-shell-extension-dash-to-dock gnome-shell-extension-appindicator openbox -r

# Nombre del usuario a crear
USERNAME="treeostempus3rx01_script"

# Crear el usuario sin contraseña
useradd -m -s /bin/bash "$USERNAME"
passwd -d "$USERNAME"

# Agregar el usuario al grupo de administradores (wheel)
usermod -aG wheel "$USERNAME"
