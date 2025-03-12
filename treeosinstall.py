#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Pango
import subprocess
import time

class SystemConfigurator:
    @staticmethod
    def create_user(username):
        # Crea el usuario con directorio home
        subprocess.run(["sudo", "useradd", "-m", username], check=True)
        # Elimina la contraseña para que se pida en el primer inicio de sesión
        subprocess.run(["sudo", "passwd", "-d", username], check=True)
        subprocess.run(["sudo", "chage", "-d", "0", username], check=True)
        # Para Fedora Silverblue, se usa el grupo wheel en lugar de sudo
        subprocess.run(["sudo", "usermod", "-aG", "wheel", username], check=True)

    @staticmethod
    def configure_localization(locale, keyboard_layout):
        try:
            # 1. Ajustar el locale del sistema
            subprocess.run([
                "sudo", "localectl", "set-locale", f"LANG={locale}"
            ], check=True)

            # 2. Ajustar el layout del teclado
            subprocess.run([
                "sudo", "localectl", "set-keymap", keyboard_layout
            ], check=True)

            # 3. Actualizar la configuración de X11
            subprocess.run([
                "sudo", "localectl", "set-x11-keymap", keyboard_layout
            ], check=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error configurando localización: {e.stderr}")

    @staticmethod
    def create_profile_d_script():
        """
        Crea el archivo /etc/profile.d/treeos_init.sh con permisos de ejecución.
        Este script clona/actualiza el repositorio Treeos y lanza el update_checker.sh en segundo plano.
        """
        script_content = r"""#!/bin/bash

# Si esta variable ya está definida, significa que el script ya corrió en esta sesión
if [[ -n "$TREEOS_UPDATE_DONE" ]]; then
  return 0
fi

# Definimos la variable para que no se ejecute más veces en esta sesión
export TREEOS_UPDATE_DONE=1

# -- 1) Lógica para clonar/actualizar Treeos --
if [ ! -d "$HOME/.local/share/applications/.git" ]; then
  git clone https://github.com/carlosvalin94/Treeos.git "$HOME/.local/share/applications/"
else
  cd "$HOME/.local/share/applications" || exit
  git fetch --all
  git reset --hard origin/main
fi

# Ajustar la ruta del icono en el archivo .desktop
sed -i "s|Icon=TEMPATH.*|Icon=$HOME/.local/share/applications/treeos-control/logo.gif|" \
  "$HOME/.local/share/applications/treeos-control.desktop"

# -- 2) Verificar si ya existe un 'update_checker.sh' corriendo para este usuario --
if pgrep -u "$USER" -f "update_checker.sh" >/dev/null 2>&1; then
  echo "update_checker.sh ya está corriendo para el usuario $USER."
  return 0
fi

# -- 3) Si no está corriendo, lo lanzamos en 2º plano con nohup --
nohup "$HOME/.local/share/applications/treeos-control/update_checker.sh" \
  >/dev/null 2>&1 &
"""

        # 1. Escribir el contenido en /etc/profile.d/treeos_init.sh
        subprocess.run([
            "sudo", "bash", "-c",
            f"cat << 'EOF' > /etc/profile.d/treeos_init.sh\n{script_content}\nEOF"
        ], check=True)

        # 2. Dar permisos de ejecución
        subprocess.run(["sudo", "chmod", "+x", "/etc/profile.d/treeos_init.sh"], check=True)

    @staticmethod
    def create_treeostempus3rx01_script():
        """
        En lugar de crear un script en /etc/profile.d/ para borrar al usuario 'treeostempus3rx01',
        creamos un servicio de systemd que se ejecutará al ARRANCAR el sistema.
        
        Este servicio:
          - Elimina al usuario 'treeostempus3rx01'
          - Se autodestruye tras ejecutarse (rm -f del .service)
        
        Al estar fuera de la sesión del usuario, evita problemas de "User is currently logged in".
        """
        service_content = r"""[Unit]
Description=Remove user treeostempus3rx01 on next boot

[Service]
Type=oneshot
ExecStart=/usr/sbin/userdel -r treeostempus3rx01
ExecStartPost=/usr/bin/rm -f /etc/systemd/system/remove-treeostempus3rx01.service

[Install]
WantedBy=multi-user.target
"""

        # 1. Escribir el archivo de unidad en /etc/systemd/system/
        subprocess.run([
            "sudo", "bash", "-c",
            f"cat << 'EOF' > /etc/systemd/system/remove-treeostempus3rx01.service\n{service_content}\nEOF"
        ], check=True)

        # 2. Recargar systemd
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        # 3. Habilitar el servicio para que corra en el próximo arranque
        subprocess.run(["sudo", "systemctl", "enable", "remove-treeostempus3rx01.service"], check=True)


class SetupWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title="TreeOS - Configuración Inicial", application=app)
        self._countdown = 10
        self._setup_ui()
        self._configure_window_properties()
        self._connect_signals()

    def _configure_window_properties(self):
        # Ventana en modo fullscreen, sin decoraciones y modal
        self.fullscreen()
        self.set_decorated(False)
        self.set_modal(True)

    def _setup_ui(self):
        self.main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=30,
            margin_top=50,
            margin_bottom=50,
            margin_start=50,
            margin_end=50
        )

        self._build_header()
        self._build_username_entry()
        self._build_localization_section()
        self._build_footer()

        self.set_child(self.main_box)

    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.title_label = Gtk.Label(
            label="Bienvenido a TreeOS - Configuración Inicial",
            css_classes=["title"],
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD
        )

        self.description_label = Gtk.Label(
            label="Por favor, configure su nombre de usuario, idioma y distribución de teclado.",
            css_classes=["subtitle"],
            wrap=True
        )

        header.append(self.title_label)
        header.append(self.description_label)
        self.main_box.append(header)

    def _build_username_entry(self):
        self.username_entry = Gtk.Entry(
            placeholder_text="Nuevo nombre de usuario",
            margin_bottom=20
        )
        self.main_box.append(self.username_entry)

    def _build_localization_section(self):
        locale_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)

        locale_label = Gtk.Label(
            label="Configuración de Idioma y Teclado",
            css_classes=["section-header"]
        )

        self._build_language_selector()
        self._build_keyboard_selector()

        locale_box.append(locale_label)
        locale_box.append(self.language_dropdown)
        locale_box.append(self.keyboard_dropdown)
        self.main_box.append(locale_box)

    def _build_language_selector(self):
        languages = {
            "en_US.utf8": "English (USA)",
            "es_ES.utf8": "Español (España)",
            "fr_FR.utf8": "Francés",
            "de_DE.utf8": "Alemán",
            "it_IT.utf8": "Italiano"
        }

        self.language_model = Gtk.StringList()
        self.locale_map = []
        for locale, name in languages.items():
            self.language_model.append(name)
            self.locale_map.append(locale)

        self.language_dropdown = Gtk.DropDown(
            model=self.language_model,
            valign=Gtk.Align.START
        )

    def _build_keyboard_selector(self):
        keyboard_layouts = {
            "us": "Inglés (USA)",
            "es": "Español",
            "fr": "Francés",
            "de": "Alemán"
        }

        self.keyboard_model = Gtk.StringList()
        self.keyboard_map = []
        for layout, name in keyboard_layouts.items():
            self.keyboard_model.append(name)
            self.keyboard_map.append(layout)

        self.keyboard_dropdown = Gtk.DropDown(model=self.keyboard_model)

    def _build_footer(self):
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)

        self.confirm_button = Gtk.Button(
            label="Aplicar Configuración",
            css_classes=["suggested-action"],
            sensitive=False
        )
        footer_box.append(self.confirm_button)

        self.shutdown_button = Gtk.Button(
            label="Apagar",
            css_classes=["destructive-action"]
        )
        self.shutdown_button.connect("clicked", self.on_shutdown)
        footer_box.append(self.shutdown_button)

        self.main_box.append(footer_box)

    def _connect_signals(self):
        self.username_entry.connect("notify::text", self._validate_fields)
        self.language_dropdown.connect("notify::selected", self._validate_fields)
        self.keyboard_dropdown.connect("notify::selected", self._validate_fields)
        self.confirm_button.connect("clicked", self._show_confirmation_dialog)

    def _validate_fields(self, *args):
        username_valid = len(self.username_entry.get_text().strip()) > 0
        lang_valid = self.language_dropdown.get_selected() != -1
        keyboard_valid = self.keyboard_dropdown.get_selected() != -1

        self.confirm_button.set_sensitive(all([username_valid, lang_valid, keyboard_valid]))

    def _show_confirmation_dialog(self, button):
        confirm_dialog = Gtk.AlertDialog()
        confirm_dialog.set_message("Confirmar configuración")
        confirm_dialog.set_detail(
            "¿Está seguro que desea aplicar esta configuración?\n"
            "El sistema se reiniciará automáticamente."
        )
        confirm_dialog.set_buttons(["Cancelar", "Aplicar"])
        confirm_dialog.set_default_button(1)
        confirm_dialog.set_cancel_button(0)

        confirm_dialog.choose(self, None, self._on_dialog_response)

    def _on_dialog_response(self, dialog, result):
        try:
            response = dialog.choose_finish(result)
            if response == 1:
                self._apply_configuration()
        except Exception as e:
            self._show_error_dialog(str(e))

    def _apply_configuration(self):
        """
        Se llama cuando el usuario confirma la configuración:
          1) Crea el usuario
          2) Configura idioma/teclado
          3) Crea /etc/profile.d/treeos_init.sh
          4) Crea y habilita un servicio systemd para eliminar 'treeostempus3rx01' en el próximo arranque
          5) Inicia cuenta regresiva para reiniciar
        """
        try:
            username = self.username_entry.get_text().strip()
            lang_index = self.language_dropdown.get_selected()
            keyboard_index = self.keyboard_dropdown.get_selected()

            locale = self.locale_map[lang_index]
            keyboard_layout = self.keyboard_map[keyboard_index]

            # 1) Crear usuario (con privilegios de administrador => grupo wheel en Fedora Silverblue)
            SystemConfigurator.create_user(username)

            # 2) Configurar localización
            SystemConfigurator.configure_localization(locale, keyboard_layout)

            # 3) Crear /etc/profile.d/treeos_init.sh
            SystemConfigurator.create_profile_d_script()

            # 4) Crear y habilitar el servicio de systemd para borrar al usuario "treeostempus3rx01"
            SystemConfigurator.create_treeostempus3rx01_script()

            # 5) Mostrar cuenta regresiva y reiniciar
            self._show_restart_countdown()

        except subprocess.CalledProcessError as e:
            self._show_error_dialog(f"Error en el sistema: {str(e)}")
        except Exception as e:
            self._show_error_dialog(str(e))

    def _show_restart_countdown(self):
        # Diálogo modal para la cuenta regresiva
        self.countdown_dialog = Gtk.Dialog(
            title="Configuración completada",
            transient_for=self,
            modal=True
        )

        # Removemos el botón de cierre (X)
        self.countdown_dialog.set_deletable(False)

        # Agregamos una etiqueta con el mensaje de cuenta regresiva
        self.countdown_label = Gtk.Label(label=f"El sistema se reiniciará en {self._countdown} segundos...")
        self.countdown_dialog.get_content_area().append(self.countdown_label)

        # Mostramos el diálogo
        self.countdown_dialog.show()

        # Iniciamos la cuenta regresiva
        GLib.timeout_add_seconds(1, self._update_countdown)

    def _update_countdown(self):
        self._countdown -= 1
        if self._countdown > 0:
            self.countdown_label.set_label(
                f"El sistema se reiniciará en {self._countdown} segundos..."
            )
            return True
        else:
            # Reiniciar el sistema
            subprocess.run(["sudo", "shutdown", "-r", "now"])
            return False

    def on_shutdown(self, button):
        shutdown_dialog = Gtk.AlertDialog()
        shutdown_dialog.set_message("Confirmar apagado")
        shutdown_dialog.set_detail("¿Está seguro que desea apagar el sistema?")
        shutdown_dialog.set_buttons(["Cancelar", "Apagar"])
        shutdown_dialog.set_default_button(1)
        shutdown_dialog.set_cancel_button(0)

        shutdown_dialog.choose(self, None, self._on_shutdown_response)

    def _on_shutdown_response(self, dialog, result):
        try:
            response = dialog.choose_finish(result)
            if response == 1:
                subprocess.run(["sudo", "shutdown", "-h", "now"])
        except Exception as e:
            self._show_error_dialog(str(e))

    def _show_error_dialog(self, message):
        error_dialog = Gtk.AlertDialog()
        error_dialog.set_message("Error de configuración")
        error_dialog.set_detail(message)
        error_dialog.show(self)

def on_activate(app):
    win = SetupWindow(app)
    win.present()

if __name__ == "__main__":
    app = Gtk.Application()
    app.connect('activate', on_activate)
    app.run(None)
