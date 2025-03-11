#!/bin/bash

# Si esta variable ya está definida, significa que el script ya corrió en esta sesión
if [[ -n "$TREEOS_UPDATE_DONE" ]]; then
  return 0
fi

# Definimos la variable para que no se ejecute más veces en esta sesión
export TREEOS_UPDATE_DONE=1

# -- AQUI VA TU LOGICA --
# Verificar si el repositorio ya fue clonado
if [ ! -d "$HOME/.local/share/applications/.git" ]; then
  # Clonar el repositorio
  git clone https://github.com/carlosvalin94/Treeos.git "$HOME/.local/share/applications/"
else
  # Entrar al directorio y actualizar el repositorio
  cd "$HOME/.local/share/applications" || exit
  git fetch --all
  git reset --hard origin/main
fi

# Actualizar la ruta del icono en el archivo .desktop
sed -i "s|Icon=TEMPATH.*|Icon=$HOME/.local/share/applications/treeos-control/logo.gif|" \
  "$HOME/.local/share/applications/treeos-control.desktop"
