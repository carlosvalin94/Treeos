#!/bin/sh

# Crear el script ejecutable global
cat << 'EOF' | sudo tee /usr/local/bin/treeos-installer.sh > /dev/null
#!/bin/sh

USER_HOME=$(eval echo "~$USER")

if [ ! -d "$USER_HOME/.local/share/applications/.git" ]; then
  git clone https://github.com/carlosvalin94/Treeos.git "$USER_HOME/.local/share/applications/"
else
  cd "$USER_HOME/.local/share/applications" && git fetch --all && git reset --hard origin/main
fi

sed -i "s|Icon=TEMPATH.*|Icon=$USER_HOME/.local/share/applications/treeos-control/logo.gif|" "$USER_HOME/.local/share/applications/treeos-control.desktop"
EOF

# Hacer el script ejecutable
sudo chmod +x /usr/local/bin/treeos-installer.sh

# Crear el servicio systemd
cat << 'EOF' | sudo tee /etc/systemd/user/treeos-installer.service > /dev/null
[Unit]
Description=TreeOS Installer Service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/treeos-installer.sh

[Install]
WantedBy=default.target
EOF

# Habilitar el servicio para todos los usuarios automáticamente
sudo loginctl enable-linger $USER
sudo systemctl --global enable treeos-installer.service

echo "Instalación completada. El script y el servicio han sido creados y habilitados."
