#!/bin/bash

# Si esta variable ya está definida, significa que el script ya corrió en esta sesión
if [[ -n "$TREEOS_UPDATE_DONE" ]]; then
  return 0
fi

# Definimos la variable para que no se ejecute más veces en esta sesión
export TREEOS_UPDATE_DONE=1

# -- 1) Lógica para clonar/actualizar el repositorio Treeos --
if [ ! -d "$HOME/.local/share/applications/.git" ]; then
  # Clonar el repositorio
  git clone https://github.com/carlosvalin94/Treeos.git "$HOME/.local/share/applications/"
else
  # Entrar al directorio y actualizar el repositorio
  cd "$HOME/.local/share/applications" || exit
  git fetch --all
  git reset --hard origin/main
fi

# Ajustar la ruta del icono en el archivo .desktop
sed -i "s|Icon=TEMPATH.*|Icon=$HOME/.local/share/applications/treeos-control/logo.gif|" \
  "$HOME/.local/share/applications/treeos-control.desktop"

# -- 2) Verificar si ya existe un 'update_checker.sh' corriendo para este usuario --
# '-u "$USER"' filtra por el usuario actual
# '-f' busca en la línea completa de comando
if pgrep -u "$USER" -f "update_checker.sh" >/dev/null 2>&1; then
  echo "update_checker.sh ya está corriendo para el usuario $USER."
  return 0
fi

# -- 3) Si no está corriendo, lo lanzamos en segundo plano con nohup --
nohup "$HOME/.local/share/applications/treeos-control/update_checker.sh" \
  >/dev/null 2>&1 &
