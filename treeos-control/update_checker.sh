#!/bin/bash
# update_checker.sh
# Comprueba y aplica actualizaciones cada cierto tiempo.

CONFIG_DIR="$HOME/.local/share/applications/treeos-control"
CONFIG_FILE="${CONFIG_DIR}/update_config.conf"
LATEST_RELEASE_FILE="${CONFIG_DIR}/latest-release"

# Función para leer la configuración
read_config() {
    # Valores por defecto
    AUTO_UPDATES_ENABLED="True"
    CHECK_FREQUENCY="daily"  # Opciones: hourly, daily, weekly
    LAST_UPDATE_CHECK="0"
    STORED_VERSION=""
    
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
        echo "$(date '+%Y-%m-%d %H:%M:%S') Archivo de config no encontrado o vacío. Usando valores por defecto."
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

# Ejecutar un comando y mostrar error si ocurre
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

# Comprobar si hay una nueva versión y hacer rebase
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
        echo "$(date '+%Y-%m-%d %H:%M:%S') No hay nuevas versiones para rebase."
    fi
}

# Obtener el intervalo en segundos según la frecuencia
get_interval() {
    case "$CHECK_FREQUENCY" in
        hourly) echo $((60*60)) ;;        # 3600
        daily)  echo $((24*60*60)) ;;     # 86400
        weekly) echo $((7*24*60*60)) ;;   # 604800
        *)      echo $((24*60*60)) ;;     # Por defecto, 86400
    esac
}

# Bucle principal
while true; do
    read_config
    current_time=$(date +%s)

    # Si nunca se ha comprobado (LAST_UPDATE_CHECK=0), forzamos "ya caducado"
    # para que se haga un chequeo inmediato.
    if [ "$LAST_UPDATE_CHECK" -eq 0 ]; then
        interval=$(get_interval)
        LAST_UPDATE_CHECK=$(( current_time - interval ))
    fi

    elapsed=$(( current_time - LAST_UPDATE_CHECK ))
    interval=$(get_interval)

    # Si ya pasó el intervalo de tiempo configurado, toca actualizar
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

    # Espera 60 segundos antes de volver a comprobar
    sleep 60
done
