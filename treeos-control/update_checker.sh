#!/bin/bash
# update_checker.sh
# Este script controla las actualizaciones de Fedora Silverblue:
# - Ejecuta 'rpm-ostree upgrade'
# - Si detecta una nueva versión (según el archivo latest-release), ejecuta 'rpm-ostree rebase <latest_version>'
# - Registra cada acción con fecha y hora
# Se ejecuta en un bucle comprobando cada 60 segundos si ha pasado el intervalo configurado.

# Rutas y directorios
USER=$(whoami)
CONFIG_DIR="/var/home/${USER}/.local/share/applications/treeos-control"
CONFIG_FILE="${CONFIG_DIR}/update_config.conf"
LATEST_RELEASE_FILE="${CONFIG_DIR}/latest-release"

# Crear el directorio de configuración si no existe
mkdir -p "$CONFIG_DIR"

# Valores por defecto
DEFAULT_AUTO_UPDATES_ENABLED="True"
DEFAULT_CHECK_FREQUENCY="daily"  # Opciones: hourly, daily, weekly
DEFAULT_LAST_UPDATE_CHECK=0
DEFAULT_STORED_VERSION=""

# Función para leer la configuración
read_config() {
    AUTO_UPDATES_ENABLED="$DEFAULT_AUTO_UPDATES_ENABLED"
    CHECK_FREQUENCY="$DEFAULT_CHECK_FREQUENCY"
    LAST_UPDATE_CHECK="$DEFAULT_LAST_UPDATE_CHECK"
    STORED_VERSION="$DEFAULT_STORED_VERSION"
    if [ -f "$CONFIG_FILE" ] && [ -s "$CONFIG_FILE" ]; then
        while IFS='=' read -r key value; do
            case "$key" in
                AUTO_UPDATES_ENABLED) AUTO_UPDATES_ENABLED="$value" ;;
                CHECK_FREQUENCY) CHECK_FREQUENCY="$value" ;;
                LAST_UPDATE_CHECK) LAST_UPDATE_CHECK="$value" ;;
                STORED_VERSION) STORED_VERSION="$value" ;;
            esac
        done < "$CONFIG_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') Archivo de configuración no encontrado o vacío. Usando valores por defecto."
    fi
}

# Función para escribir la configuración
write_config() {
    cat <<EOF > "$CONFIG_FILE"
AUTO_UPDATES_ENABLED=$AUTO_UPDATES_ENABLED
CHECK_FREQUENCY=$CHECK_FREQUENCY
LAST_UPDATE_CHECK=$LAST_UPDATE_CHECK
STORED_VERSION=$STORED_VERSION
EOF
}

# Función para ejecutar un comando y mostrar error si ocurre
ejecutar_comando() {
    if ! eval "$1"; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Error ejecutando: $1"
    fi
}

# Función para aplicar actualizaciones
apply_updates() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') Aplicando actualizaciones del sistema..."
    ejecutar_comando "rpm-ostree upgrade"
}

# Función para comprobar si hay una nueva versión y aplicar rebase si es necesario
check_silverblue_version() {
    if [ -f "$LATEST_RELEASE_FILE" ]; then
        latest=$(tr -d ' \t\n\r' < "$LATEST_RELEASE_FILE")
    else
        latest=""
    fi

    if [ -n "$latest" ] && [ "$latest" != "$STORED_VERSION" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Nueva versión disponible: $latest. Aplicando rebase..."
        ejecutar_comando "rpm-ostree rebase $latest"
        STORED_VERSION="$latest"
        write_config
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') No hay nuevas versiones."
    fi
}

# Función para obtener el intervalo en segundos según la frecuencia
get_interval() {
    case "$CHECK_FREQUENCY" in
        hourly) echo $((60*60)) ;;       # 3600 segundos
        daily) echo $((24*60*60)) ;;       # 86400 segundos
        weekly) echo $((7*24*60*60)) ;;    # 604800 segundos
        *) echo $((24*60*60)) ;;           # Por defecto, 86400 segundos
    esac
}

# Bucle principal: cada 60 segundos se comprueba si ya pasó el intervalo configurado
while true; do
    read_config
    current=$(date +%s)
    # Si nunca se ha comprobado, forzamos la actualización inmediatamente
    if [ "$LAST_UPDATE_CHECK" -eq 0 ]; then
        interval=$(get_interval)
        LAST_UPDATE_CHECK=$(( current - interval ))
    fi
    elapsed=$(( current - LAST_UPDATE_CHECK ))
    interval=$(get_interval)
    if [ "$elapsed" -ge "$interval" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Iniciando comprobación de actualizaciones..."
        apply_updates
        check_silverblue_version
        LAST_UPDATE_CHECK=$(date +%s)
        write_config
    else
        remaining=$(( interval - elapsed ))
        echo "$(date '+%Y-%m-%d %H:%M:%S') Quedan $remaining segundos para el próximo chequeo."
    fi
    sleep 60
done

