import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Pango
import subprocess
import re
import time

class SystemConfigurator:
    @staticmethod
    def create_user(username):
        subprocess.run(["sudo", "useradd", "-m", username], check=True)
        subprocess.run(["sudo", "passwd", "-d", username], check=True)
        subprocess.run(["sudo", "chage", "-d", "0", username], check=True)

    @staticmethod
    def configure_localization(locale, keyboard_layout):
        try:
            # Set the system locale
            subprocess.run([
                "sudo", "localectl", "set-locale", f"LANG={locale}"
            ], check=True)
            
            # Set the keyboard layout
            subprocess.run([
                "sudo", "localectl", "set-keymap", keyboard_layout
            ], check=True)
            
            # Update the locale environment
            subprocess.run([
                "sudo", "localectl", "set-x11-keymap", keyboard_layout
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error configuring localization: {e.stderr}")

    @staticmethod
    def remove_temp_user():
        try:
            # Attempt to create the removal script
            subprocess.run([
                "sudo", "bash", "-c", 
                "echo -e '#!/bin/bash\n"
                "if id \"bubu\" &>/dev/null; then\n"
                "  userdel -r bubu\n"
                "fi' > /var/usermod_remove_bubu.sh"
            ], check=True)
            
            # Make the script executable
            subprocess.run([
                "sudo", "chmod", "+x", "/var/usermod_remove_bubu.sh"
            ], check=True)
            
            # Create the systemd service
            subprocess.run([
                "sudo", "bash", "-c", 
                "echo -e '[Unit]\n"
                "Description=Eliminar usuario bubu\n"
                "After=systemd-user-sessions.service\n"
                "Before=gdm.service\n\n"
                "[Service]\n"
                "ExecStart=/var/usermod_remove_bubu.sh\n"
                "Type=oneshot\n"
                "RemainAfterExit=true\n\n"
                "[Install]\n"
                "WantedBy=multi-user.target' > /etc/systemd/system/remove_bubu.service"
            ], check=True)
            
            # Enable and start the service
            subprocess.run([
                "sudo", "systemctl", "enable", "remove_bubu.service"
            ], check=True)
            
            subprocess.run([
                "sudo", "systemctl", "start", "remove_bubu.service"
            ], check=True)
            
        except subprocess.CalledProcessError:
            # Ignore errors and continue
            pass

class SetupWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title="TreeOS - Configuración Inicial", application=app)
        self._countdown = 10
        self._setup_ui()
        self._configure_window_properties()
        self._connect_signals()

    def _configure_window_properties(self):
        # Set the window to fullscreen
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
            "fr_FR.utf8": "Français",
            "de_DE.utf8": "Deutsch",
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
            "fr": "Français",
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
        try:
            username = self.username_entry.get_text().strip()
            lang_index = self.language_dropdown.get_selected()
            keyboard_index = self.keyboard_dropdown.get_selected()
            
            locale = self.locale_map[lang_index]
            keyboard_layout = self.keyboard_map[keyboard_index]

            SystemConfigurator.create_user(username)
            SystemConfigurator.configure_localization(locale, keyboard_layout)
            SystemConfigurator.remove_temp_user()
            
            self._show_restart_countdown()

        except subprocess.CalledProcessError as e:
            self._show_error_dialog(f"Error en el sistema: {str(e)}")
        except Exception as e:
            self._show_error_dialog(str(e))

    def _show_restart_countdown(self):
        # Create a modal dialog
        self.countdown_dialog = Gtk.Dialog(
            title="Configuración completada",
            transient_for=self,
            modal=True
        )
        
        # Remove the close button (X) from the dialog
        self.countdown_dialog.set_deletable(False)
        
        # Add a label for the countdown message
        self.countdown_label = Gtk.Label(label=f"El sistema se reiniciará en {self._countdown} segundos...")
        self.countdown_dialog.get_content_area().append(self.countdown_label)
        
        # Show the dialog
        self.countdown_dialog.show()
        
        # Start the countdown
        GLib.timeout_add_seconds(1, self._update_countdown)

    def _update_countdown(self):
        self._countdown -= 1
        if self._countdown > 0:
            # Update the countdown message
            self.countdown_label.set_label(f"El sistema se reiniciará en {self._countdown} segundos...")
            return True
        else:
            # Restart the system
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
