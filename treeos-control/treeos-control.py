#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, GdkPixbuf, Gio
import subprocess, os, time, threading
from datetime import datetime

# Rutas y variables de configuración
USER = os.getenv("USER")
BASE_DIR = f"/var/home/{USER}/.local/share/applications/treeos-control"
CONFIG_FILE = os.path.join(BASE_DIR, "update_config.conf")
MANUAL_FILE = os.path.join(BASE_DIR, "treeosmanual.pdf")
LATEST_RELEASE_FILE = os.path.join(BASE_DIR, "latest-release")
APP_ICON = os.path.join(BASE_DIR, "logo.gif")  # Icono de la aplicación

# Dimensiones y márgenes
WINDOW_WIDTH = 750
WINDOW_HEIGHT = 600
SMALL_IMAGE_SIZE = 150
WALLPAPER_IMAGE_SIZE = 150
MARGIN = 10

# Lock file para actualizaciones manuales
LOCK_FILE = "/tmp/treeos_update.lock"

# Configuración por defecto
DEFAULT_CONFIG = {
    "AUTO_UPDATES_ENABLED": True,
    "CHECK_FREQUENCY": "daily",  # Opciones: hourly, daily, weekly
    "EXTENSIONES_HABILITADAS": False,
    "FIRST_BOOT": True,
    "LAST_UPDATE_CHECK": 0,
    "STORED_VERSION": ""
}

def read_config():
    config = DEFAULT_CONFIG.copy()
    if os.path.isfile(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 0:
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and line:
                    try:
                        key, value = line.split("=", 1)
                        key, value = key.strip(), value.strip()
                        if key in ["AUTO_UPDATES_ENABLED", "EXTENSIONES_HABILITADAS", "FIRST_BOOT"]:
                            config[key] = (value.lower() == "true")
                        elif key in ["LAST_UPDATE_CHECK"]:
                            config[key] = int(value)
                        else:
                            config[key] = value
                    except ValueError:
                        print(f"Línea malformada: {line}")
    else:
        print("Archivo de configuración no encontrado o vacío. Usando valores por defecto.")
    return config

def write_config(auto_updates_enabled=None, check_frequency=None, extensiones_habilitadas=None,
                 first_boot=None, last_update_check=None, stored_version=None):
    if not os.path.isfile(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
        with open(CONFIG_FILE, 'w') as f:
            f.write(f"AUTO_UPDATES_ENABLED={str(auto_updates_enabled if auto_updates_enabled is not None else DEFAULT_CONFIG['AUTO_UPDATES_ENABLED']).lower()}\n")
            f.write(f"CHECK_FREQUENCY={check_frequency if check_frequency is not None else DEFAULT_CONFIG['CHECK_FREQUENCY']}\n")
            f.write(f"EXTENSIONES_HABILITADAS={str(extensiones_habilitadas if extensiones_habilitadas is not None else DEFAULT_CONFIG['EXTENSIONES_HABILITADAS']).lower()}\n")
            f.write(f"FIRST_BOOT={str(first_boot if first_boot is not None else DEFAULT_CONFIG['FIRST_BOOT']).lower()}\n")
            f.write(f"LAST_UPDATE_CHECK={last_update_check if last_update_check is not None else DEFAULT_CONFIG['LAST_UPDATE_CHECK']}\n")
            f.write(f"STORED_VERSION={stored_version if stored_version is not None else DEFAULT_CONFIG['STORED_VERSION']}\n")
        print("Archivo de configuración creado con valores por defecto.")
        return

    def sed_replace(key, val):
        return f"sed -i 's|^{key}=.*|{key}={val}|' {CONFIG_FILE}"
    if auto_updates_enabled is not None:
        subprocess.run(sed_replace("AUTO_UPDATES_ENABLED", str(auto_updates_enabled).lower()), shell=True)
    if check_frequency is not None:
        subprocess.run(sed_replace("CHECK_FREQUENCY", check_frequency), shell=True)
    if extensiones_habilitadas is not None:
        subprocess.run(sed_replace("EXTENSIONES_HABILITADAS", str(extensiones_habilitadas).lower()), shell=True)
    if first_boot is not None:
        subprocess.run(sed_replace("FIRST_BOOT", str(first_boot).lower()), shell=True)
    if last_update_check is not None:
        subprocess.run(sed_replace("LAST_UPDATE_CHECK", str(last_update_check)), shell=True)
    if stored_version is not None:
        subprocess.run(sed_replace("STORED_VERSION", stored_version), shell=True)
    print("Configuración guardada.")

def ejecutar_comando(comando):
    try:
        subprocess.run(comando, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando {comando}: {e}")

def ejecutar_comando_captura(comando, callback_line=None):
    process = subprocess.Popen(comando, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True)
    for line in iter(process.stdout.readline, ''):
        if callback_line:
            callback_line(line.rstrip())
    process.stdout.close()
    process.wait()
    return process.returncode

def send_notification(title, message):
    try:
        subprocess.Popen(f'notify-send "{title}" "{message}"', shell=True)
    except Exception as e:
        print(f"Error enviando notificación: {e}")

def apply_updates_py(callback_line):
    print("Aplicando actualizaciones del sistema...")
    cmd = "rpm-ostree upgrade"
    return ejecutar_comando_captura(cmd, callback_line)

def check_silverblue_version_py(callback_line):
    print("Verificando la última versión de Fedora Silverblue...")
    if os.path.isfile(LATEST_RELEASE_FILE):
        with open(LATEST_RELEASE_FILE) as f:
            latest_version = f.read().strip()
    else:
        latest_version = ""
    config = read_config()
    stored_version = config.get("STORED_VERSION", "")
    if latest_version and latest_version != stored_version:
        send_notification("Nueva versión", f"Nueva versión disponible: {latest_version}. Aplicando rebase...")
        if callback_line:
            callback_line(f"Aplicando rebase a la versión: {latest_version}")
        cmd = f"rpm-ostree rebase {latest_version}"
        rcode = ejecutar_comando_captura(cmd, callback_line)
        if rcode == 0:
            send_notification("Actualización completada", f"Silverblue actualizado a {latest_version}.")
            if callback_line:
                callback_line(f"Rebase completado a la versión: {latest_version}")
        else:
            send_notification("Error", f"Ocurrió un error al aplicar rebase a {latest_version}.")
        write_config(stored_version=latest_version)
    else:
        if callback_line:
            callback_line("No hay nuevas versiones de Silverblue disponibles.")

# Toolbox Helper
def ensure_toolbox_exists():
    try:
        output = subprocess.check_output("toolbox list", shell=True, text=True)
        if "treeossecure" not in output:
            print("Contenedor 'treeossecure' no encontrado. Creándolo automáticamente...")
            subprocess.run("toolbox create --yes -c treeossecure", shell=True, check=True)
            time.sleep(5)
    except subprocess.CalledProcessError as e:
        print("Error al verificar o crear el contenedor:", e)

# Información para .desktop
APPS_DESKTOP = {
    "pycharm": {
        "package": "pycharm-community",
        "desktop_file": "pycharm-toolbox.desktop",
        "name": "PyCharm (Toolbox)",
        "comment": "IDE for Python Development",
        "icon": "pycharm"
    },
    "vscode": {
        "package": "code",
        "desktop_file": "vscode-toolbox.desktop",
        "name": "VS Code (Toolbox)",
        "comment": "Code Editor",
        "icon": "code"
    },
    "anaconda": {
        "package": "anaconda",
        "desktop_file": "anaconda-toolbox.desktop",
        "name": "Anaconda (Toolbox)",
        "comment": "Python Distribution",
        "icon": "anaconda"
    }
}

def crear_desktop_app(app_key):
    data = APPS_DESKTOP[app_key]
    desktop_path = os.path.expanduser(f"~/.local/share/applications/{data['desktop_file']}")
    content = (
        f"[Desktop Entry]\n"
        f"Name={data['name']}\n"
        f"Comment={data['comment']}\n"
        f"Exec=toolbox run --container treeossecure {data['package']}\n"
        f"Icon={data['icon']}\n"
        f"Terminal=false\n"
        f"Type=Application\n"
        f"Categories=Development;IDE;\n"
    )
    comando = f'echo -e "{content}" | tee {desktop_path} && chmod +x {desktop_path}'
    return comando

# Control Panel Window
class ControlPanelWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Treeos Control Panel")
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.changing_theme = False
        self.set_custom_window_icon(APP_ICON)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=MARGIN)
        main_box.set_margin_top(MARGIN)
        main_box.set_margin_bottom(MARGIN)
        main_box.set_margin_start(MARGIN)
        main_box.set_margin_end(MARGIN)
        self.set_child(main_box)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.START)
        switcher.set_margin_bottom(MARGIN)
        main_box.append(switcher)
        main_box.append(self.stack)

        self.build_apariencia_page()
        self.build_actualizaciones_page()
        self.build_treeos_ayuda_page()
        self.build_treeos_secure_page()

        self.stack.set_visible_child_name("Apariencia")
        if not os.path.exists(CONFIG_FILE):
            self.toggle_traditional.set_active(True)

    def set_custom_window_icon(self, icon_path):
        if os.path.isfile(icon_path):
            try:
                icon = Gio.FileIcon.new(Gio.File.new_for_path(icon_path))
                self.set_icon(icon)
            except Exception as e:
                print(f"No se pudo cargar el icono: {e}")
        else:
            print(f"Icono no encontrado: {icon_path}")

    def switch_to(self, page_name):
        self.stack.set_visible_child_name(page_name)
        self.present()

    # Página: Apariencia
    def build_apariencia_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=MARGIN)
        header = Gtk.Label()
        header.set_markup("<span size='xx-large' weight='bold'>Apariencia</span>")
        header.set_margin_bottom(MARGIN)
        box.append(header)

        theme_frame = Gtk.Frame(label="Temas")
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        theme_box.set_margin_top(MARGIN)
        theme_box.set_margin_bottom(MARGIN)
        theme_box.set_margin_start(MARGIN)
        theme_box.set_margin_end(MARGIN)
        theme_box.set_halign(Gtk.Align.CENTER)
        theme_frame.set_child(theme_box)

        # Botón Traditional
        self.toggle_traditional = Gtk.ToggleButton()
        vbox_traditional = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        img_traditional = Gtk.Image.new_from_file(os.path.join(BASE_DIR, "traditional.png"))
        img_traditional.set_pixel_size(SMALL_IMAGE_SIZE)
        label_traditional = Gtk.Label(label="Traditional")
        vbox_traditional.append(img_traditional)
        vbox_traditional.append(label_traditional)
        self.toggle_traditional.set_child(vbox_traditional)
        self.toggle_traditional.connect("toggled", self.on_traditional_toggled)
        theme_box.append(self.toggle_traditional)

        # Botón Modern
        self.toggle_modern = Gtk.ToggleButton()
        vbox_modern = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        img_modern = Gtk.Image.new_from_file(os.path.join(BASE_DIR, "modern.png"))
        img_modern.set_pixel_size(SMALL_IMAGE_SIZE)
        label_modern = Gtk.Label(label="Modern")
        vbox_modern.append(img_modern)
        vbox_modern.append(label_modern)
        self.toggle_modern.set_child(vbox_modern)
        self.toggle_modern.connect("toggled", self.on_modern_toggled)
        theme_box.append(self.toggle_modern)

        box.append(theme_frame)

        # Fondos
        wallpaper_frame = Gtk.Frame(label="Fondos Oficiales de Treeos")
        wallpaper_box = Gtk.Grid()
        wallpaper_box.set_row_spacing(MARGIN)
        wallpaper_box.set_column_spacing(MARGIN)
        wallpaper_box.set_margin_top(MARGIN)
        wallpaper_box.set_margin_bottom(MARGIN)
        wallpaper_box.set_margin_start(MARGIN)
        wallpaper_box.set_margin_end(MARGIN)
        wallpaper_box.set_halign(Gtk.Align.CENTER)

        num_wallpapers = 6
        cols = 3
        for i in range(1, num_wallpapers + 1):
            btn = Gtk.Button()
            wallpaper_path = os.path.join(BASE_DIR, f"treeoswallpaper{i:02d}.webp")
            img_wallpaper = Gtk.Image.new_from_file(wallpaper_path)
            img_wallpaper.set_pixel_size(WALLPAPER_IMAGE_SIZE)
            btn.set_child(img_wallpaper)
            btn.set_tooltip_text(f"Fondo {i}")
            btn.connect("clicked", self.seleccionar_fondo, wallpaper_path)
            col = (i - 1) % cols
            row = (i - 1) // cols
            wallpaper_box.attach(btn, col, row, 1, 1)

        wallpaper_frame.set_child(wallpaper_box)
        box.append(wallpaper_frame)

        more_options_btn = Gtk.Button(label="Para más opciones de apariencia")
        more_options_btn.connect("clicked", lambda w: subprocess.Popen("gnome-control-center appearance", shell=True))
        box.append(more_options_btn)

        self.stack.add_titled(box, "Apariencia", "Apariencia")

    def on_traditional_toggled(self, button):
        if self.changing_theme:
            return
        self.changing_theme = True
        if button.get_active():
            if self.toggle_modern.get_active():
                self.toggle_modern.set_active(False)
            self.activar_traditional()
        else:
            if not self.toggle_modern.get_active():
                button.set_active(True)
        self.changing_theme = False

    def on_modern_toggled(self, button):
        if self.changing_theme:
            return
        self.changing_theme = True
        if button.get_active():
            if self.toggle_traditional.get_active():
                self.toggle_traditional.set_active(False)
            self.activar_modern()
        else:
            if not self.toggle_traditional.get_active():
                button.set_active(True)
        self.changing_theme = False

    def activar_traditional(self):
        # Primero deshabilita la extensión opuesta y luego habilita las propias del tema
        ejecutar_comando("gnome-extensions disable dash-to-dock@micxgx.gmail.com || true && "
                         "gnome-extensions enable blur-my-shell@aunetx || true && "
                         "gnome-extensions enable dash-to-panel@jderose9.github.com || true")

    def activar_modern(self):
        # Primero deshabilita la extensión opuesta y luego habilita las propias del tema
        ejecutar_comando("gnome-extensions disable dash-to-panel@jderose9.github.com || true && "
                         "gnome-extensions enable blur-my-shell@aunetx || true && "
                         "gnome-extensions enable dash-to-dock@micxgx.gmail.com || true")

    def seleccionar_fondo(self, button, wallpaper_path):
        comando = f"gsettings set org.gnome.desktop.background picture-uri 'file://{wallpaper_path}'"
        ejecutar_comando(comando)

    # Página: Actualizaciones
    def build_actualizaciones_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        header = Gtk.Label()
        header.set_markup("<span size='xx-large' weight='bold'>Actualizaciones</span>")
        header.set_margin_bottom(MARGIN)
        box.append(header)

        freq_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        freq_label = Gtk.Label(label="Frecuencia de Actualizaciones:")
        freq_label.set_halign(Gtk.Align.START)
        freq_box.append(freq_label)

        self.freq_combo = Gtk.ComboBoxText()
        self.freq_combo.append_text("Diariamente")
        self.freq_combo.append_text("Semanalmente")
        self.freq_combo.append_text("Mensualmente")
        freq_map = {"daily": 0, "weekly": 1, "monthly": 2}
        config = read_config()
        config_frequency = config.get("CHECK_FREQUENCY", "daily")
        active_index = freq_map.get(config_frequency, 0)
        self.freq_combo.set_active(active_index)

        def on_freq_changed(combo):
            idx = combo.get_active()
            reverse_map = {0: "daily", 1: "weekly", 2: "monthly"}
            frecuencia = reverse_map.get(idx, "daily")
            write_config(check_frequency=frecuencia)

        self.freq_combo.connect("changed", on_freq_changed)
        freq_box.append(self.freq_combo)
        box.append(freq_box)

        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        auto_label = Gtk.Label(label="Actualizaciones Automáticas:")
        auto_label.set_halign(Gtk.Align.START)
        auto_box.append(auto_label)

        self.auto_updates_switch = Gtk.Switch()
        self.auto_updates_switch.set_size_request(40, 20)
        self.auto_updates_switch.set_valign(Gtk.Align.CENTER)
        self.auto_updates_switch.set_active(config.get("AUTO_UPDATES_ENABLED", True))
        self.auto_updates_switch.connect("state-set", lambda s, state: write_config(auto_updates_enabled=state))
        auto_box.append(self.auto_updates_switch)
        box.append(auto_box)

        self.btn_update_now = Gtk.Button(label="Actualizar Ahora")
        self.btn_update_now.connect("clicked", self.actualizar_sistema)
        box.append(self.btn_update_now)

        self.spinner = Gtk.Spinner()
        box.append(self.spinner)

        self.img_complete = Gtk.Image.new_from_icon_name("emblem-default")
        self.img_complete.set_pixel_size(48)
        self.img_complete.set_visible(False)
        box.append(self.img_complete)

        self.details_button = Gtk.Button(label="Ver Detalles")
        self.details_button.connect("clicked", self.on_details_clicked)
        box.append(self.details_button)

        self.details_scrolled = Gtk.ScrolledWindow()
        self.details_scrolled.set_vexpand(True)
        self.details_scrolled.set_hexpand(True)
        self.details_scrolled.set_visible(False)
        self.details_textview = Gtk.TextView()
        self.details_textview.set_editable(False)
        self.details_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.details_scrolled.set_child(self.details_textview)
        box.append(self.details_scrolled)

        self.stack.add_titled(box, "Actualizaciones", "Actualizaciones")

    def on_details_clicked(self, button):
        visible = not self.details_scrolled.get_visible()
        self.details_scrolled.set_visible(visible)
        button.set_label("Ocultar Detalles" if visible else "Ver Detalles")

    def actualizar_sistema(self, button):
        if os.path.exists(LOCK_FILE):
            self.append_details_text("¡Ya se está ejecutando una actualización! Espere a que finalice.")
            GLib.idle_add(self.mostrar_imagen_completa)
            return
        try:
            with open(LOCK_FILE, "w") as f:
                f.write(str(os.getpid()))
            self.btn_update_now.set_sensitive(False)
            self.spinner.start()
            self.img_complete.set_visible(False)
            self.clear_details_text()
            self.append_details_text("Iniciando actualización manual...")
            threading.Thread(target=self.procesar_actualizacion, daemon=True).start()
        finally:
            # La eliminación del lock se realizará en procesar_actualizacion
            pass

    def procesar_actualizacion(self):
        try:
            apply_updates_py(self.append_details_text)
            check_silverblue_version_py(self.append_details_text)
            self.append_details_text("Actualización manual completada.")
        finally:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
            GLib.idle_add(self.mostrar_imagen_completa)

    def mostrar_imagen_completa(self):
        self.spinner.stop()
        self.img_complete.set_visible(True)
        self.btn_update_now.set_sensitive(True)

    def append_details_text(self, line):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        GLib.idle_add(self._append_details_text_idle, f"[{now}] {line}")

    def _append_details_text_idle(self, line):
        buffer = self.details_textview.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, line + "\n")

    def clear_details_text(self):
        buffer = self.details_textview.get_buffer()
        buffer.set_text("")

    # Página: Treeos Ayuda
    def build_treeos_ayuda_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=MARGIN)
        header = Gtk.Label()
        header.set_markup("<span size='xx-large' weight='bold'>Treeos Ayuda</span>")
        header.set_margin_bottom(MARGIN)
        box.append(header)

        guide_text = (
            "Treeos es una plataforma innovadora que combina la familiaridad de Windows "
            "con la flexibilidad de Linux. Utilice esta sección para aprender a usar Treeos "
            "y sacar el máximo provecho de sus funcionalidades."
        )
        guide_label = Gtk.Label(label=guide_text)
        guide_label.set_wrap(True)
        guide_label.set_wrap_mode(Gtk.WrapMode.WORD)
        guide_label.set_margin_bottom(MARGIN)
        box.append(guide_label)

        manual_btn = Gtk.Button(label="Abrir Manual de Usuario")
        manual_btn.connect("clicked", self.abrir_manual)
        box.append(manual_btn)

        self.stack.add_titled(box, "Treeos Ayuda", "Treeos Ayuda")

    def abrir_manual(self, button):
        try:
            subprocess.Popen(f"xdg-open '{MANUAL_FILE}'", shell=True)
        except Exception as e:
            print(f"Error al abrir el manual: {e}")

    # Página: Treeos Secure
    def build_treeos_secure_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=MARGIN)
        header = Gtk.Label()
        header.set_markup("<span size='xx-large' weight='bold'>Treeos Secure</span>")
        header.set_margin_bottom(MARGIN)
        box.append(header)

        desc = Gtk.Label(label="Instala rápidamente herramientas de desarrollo dentro del toolbox treeossecure:")
        desc.set_margin_bottom(MARGIN)
        box.append(desc)

        toolbox_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=MARGIN)

        btn_pycharm = Gtk.Button(label="Instalar PyCharm")
        btn_pycharm.connect("clicked", self.instalar_app, "pycharm")
        toolbox_buttons.append(btn_pycharm)

        btn_vscode = Gtk.Button(label="Instalar VS Code")
        btn_vscode.connect("clicked", self.instalar_app, "vscode")
        toolbox_buttons.append(btn_vscode)

        btn_anaconda = Gtk.Button(label="Instalar Anaconda")
        btn_anaconda.connect("clicked", self.instalar_app, "anaconda")
        toolbox_buttons.append(btn_anaconda)

        box.append(toolbox_buttons)

        terminal_btn = Gtk.Button(label="Abrir Terminal en Toolbox")
        terminal_btn.connect("clicked", self.abrir_terminal_toolbox)
        box.append(terminal_btn)

        self.secure_details_button = Gtk.Button(label="Ver Progreso")
        self.secure_details_button.connect("clicked", self.on_secure_details_clicked)
        box.append(self.secure_details_button)

        self.secure_details_scrolled = Gtk.ScrolledWindow()
        self.secure_details_scrolled.set_vexpand(True)
        self.secure_details_scrolled.set_hexpand(True)
        self.secure_details_scrolled.set_visible(False)
        self.secure_details_textview = Gtk.TextView()
        self.secure_details_textview.set_editable(False)
        self.secure_details_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.secure_details_scrolled.set_child(self.secure_details_textview)
        box.append(self.secure_details_scrolled)

        self.secure_spinner = Gtk.Spinner()
        box.append(self.secure_spinner)

        self.secure_img_complete = Gtk.Image.new_from_icon_name("emblem-default")
        self.secure_img_complete.set_pixel_size(48)
        self.secure_img_complete.set_visible(False)
        box.append(self.secure_img_complete)

        self.stack.add_titled(box, "Treeos Secure", "Treeos Secure")

    def on_secure_details_clicked(self, button):
        visible = not self.secure_details_scrolled.get_visible()
        self.secure_details_scrolled.set_visible(visible)
        button.set_label("Ocultar Progreso" if visible else "Ver Progreso")

    def append_secure_details_text(self, line):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        GLib.idle_add(self._append_secure_details_text_idle, f"[{now}] {line}")

    def _append_secure_details_text_idle(self, line):
        buffer = self.secure_details_textview.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, line + "\n")

    def clear_secure_details_text(self):
        buffer = self.secure_details_textview.get_buffer()
        buffer.set_text("")

    def mostrar_secure_imagen_completa(self):
        self.secure_spinner.stop()
        self.secure_img_complete.set_visible(True)

    def instalar_app(self, button, app_key):
        ensure_toolbox_exists()
        if app_key == "pycharm":
            install_cmd = (
                "toolbox run --container treeossecure bash -c \""
                "echo -e '[copr:copr.fedorainfracloud.org:phracek:PyCharm]\\n"
                "name=Copr repo for PyCharm owned by phracek\\n"
                "baseurl=https://download.copr.fedorainfracloud.org/results/phracek/PyCharm/fedora-$releasever-$basearch/\\n"
                "type=rpm-md\\n"
                "skip_if_unavailable=True\\n"
                "gpgcheck=1\\n"
                "gpgkey=https://download.copr.fedorainfracloud.org/results/phracek/PyCharm/pubkey.gpg\\n"
                "repo_gpgcheck=0\\n"
                "enabled=1\\n"
                "enabled_metadata=1\" | sudo tee -a /etc/yum.repos.d/phracek-pycharm.repo && sudo dnf install -y python3-tkinter pycharm-community libXtst xorg-x11-server-Xvfb"
            )
        elif app_key == "vscode":
            install_cmd = "toolbox run -c treeossecure dnf install -y code"
        elif app_key == "anaconda":
            install_cmd = "toolbox run -c treeossecure dnf install -y anaconda"
        else:
            install_cmd = ""

        if install_cmd:
            threading.Thread(target=lambda: self.run_install_secure(app_key, install_cmd), daemon=True).start()
        else:
            send_notification("Error", f"No se definió comando para {app_key}.")

    def run_install_secure(self, app_key, install_cmd):
        self.secure_details_scrolled.set_visible(True)
        self.secure_spinner.start()
        self.secure_img_complete.set_visible(False)
        self.clear_secure_details_text()

        self.append_secure_details_text("Verificando contenedor 'treeossecure'...")
        ensure_toolbox_exists()
        self.append_secure_details_text("Contenedor 'treeossecure' listo.")

        self.append_secure_details_text(f"Iniciando instalación de {APPS_DESKTOP[app_key]['name']}...")
        ejecutar_comando_captura(install_cmd, self.append_secure_details_text)
        self.append_secure_details_text(f"Instalación de {APPS_DESKTOP[app_key]['name']} completada.")

        desktop_cmd = crear_desktop_app(app_key)
        ejecutar_comando(desktop_cmd)
        self.append_secure_details_text("Archivo .desktop creado.")

        send_notification("Instalación", f"{APPS_DESKTOP[app_key]['name']} instalado en toolbox treeossecure.")
        GLib.idle_add(self.mostrar_secure_imagen_completa)

    def abrir_terminal_toolbox(self, button):
        ensure_toolbox_exists()
        try:
            subprocess.Popen("ptyxis -x 'toolbox enter treeossecure'", shell=True)
        except Exception as e:
            print(f"Error al abrir la terminal en toolbox: {e}")


# Aplicación principal
class Aplicacion(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.treeoscontrol.app")
        self.connect("activate", self.on_activate)
        self.control_panel = None

    def on_activate(self, app):
        self.control_panel = ControlPanelWindow(app)
        self.control_panel.present()

if __name__ == "__main__":
    APPS_DESKTOP = {
        "pycharm": {
            "package": "pycharm-community",
            "desktop_file": "pycharm-toolbox.desktop",
            "name": "PyCharm (Toolbox)",
            "comment": "IDE for Python Development",
            "icon": "pycharm"
        },
        "vscode": {
            "package": "code",
            "desktop_file": "vscode-toolbox.desktop",
            "name": "VS Code (Toolbox)",
            "comment": "Code Editor",
            "icon": "code"
        },
        "anaconda": {
            "package": "anaconda",
            "desktop_file": "anaconda-toolbox.desktop",
            "name": "Anaconda (Toolbox)",
            "comment": "Python Distribution",
            "icon": "anaconda"
        }
    }
    app = Aplicacion()
    app.run()
