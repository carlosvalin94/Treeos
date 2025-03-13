#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, GdkPixbuf
import subprocess, os, threading, sys, fcntl, re
from datetime import datetime

# ========================================
# RUTAS, CONFIGURACIONES Y VARIABLES
# ========================================
USER = os.getenv("USER")
BASE_DIR = f"/var/home/{USER}/.local/share/applications/treeos-control"
CONFIG_FILE = os.path.join(BASE_DIR, "update_config.conf")
MANUAL_FILE = os.path.join(BASE_DIR, "treeosmanual.pdf")
LATEST_RELEASE_FILE = os.path.join(BASE_DIR, "latest-release")

# Usamos logo.gif en lugar de logo.png
APP_ICON = os.path.join(BASE_DIR, "logo.gif")

WINDOW_WIDTH = 750
WINDOW_HEIGHT = 600
SMALL_IMAGE_SIZE = 150
WALLPAPER_IMAGE_SIZE = 150
MARGIN = 10

LOCK_FILE = "/tmp/treeos_update.lock"  # usado para actualizaciones

DEFAULT_CONFIG = {
    "AUTO_UPDATES_ENABLED": True,
    "CHECK_FREQUENCY": "daily",  # daily, weekly, monthly
    "EXTENSIONES_HABILITADAS": False,
    "FIRST_BOOT": True,
    "LAST_UPDATE_CHECK": 0,
    "STORED_VERSION": ""
}

# Diccionario de apps para .desktop con rutas actualizadas:
# ~/.local/share/applications/anaconda-treeossecure.desktop
# ~/.local/share/applications/pycharm-treeossecure.desktop
# ~/.local/share/applications/vscode-treeossecure.desktop
APPS_DESKTOP = {
    "pycharm": {
        "package": "pycharm-community",
        "desktop_file": "pycharm-treeossecure.desktop",
        "name": "PyCharm (Toolbox)",
        "comment": "IDE for Python Development",
        "icon": "pycharm"
    },
    "vscode": {
        "package": "code",
        "desktop_file": "vscode-treeossecure.desktop",
        "name": "VS Code (Toolbox)",
        "comment": "Code Editor",
        "icon": "code"
    },
    "anaconda": {
        "package": "anaconda",
        "desktop_file": "anaconda-treeossecure.desktop",
        "name": "Anaconda (Toolbox)",
        "comment": "Python Distribution",
        "icon": "anaconda"
    }
}

# ----------------------------------------
# Funci�n auxiliar para detectar instalaci�n
# ----------------------------------------
def is_app_installed(app_key):
    data = APPS_DESKTOP[app_key]
    desktop_path = os.path.expanduser(f"~/.local/share/applications/{data['desktop_file']}")
    return os.path.exists(desktop_path)

# ========================================
# FUNCIONES DE CONFIGURACI�N
# ========================================
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
                        elif key == "LAST_UPDATE_CHECK":
                            config[key] = int(value)
                        else:
                            config[key] = value
                    except ValueError:
                        print(f"L�nea malformada: {line}")
    else:
        print("Archivo de configuraci�n no encontrado o vac�o. Usando valores por defecto.")
    return config

def write_config(auto_updates_enabled=None, check_frequency=None, extensiones_habilitadas=None,
                 first_boot=None, last_update_check=None, stored_version=None):
    def sed_replace(key, val):
        return f"sed -i 's|^{key}=.*|{key}={val}|' {CONFIG_FILE}"
    if not os.path.isfile(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
        with open(CONFIG_FILE, 'w') as f:
            f.write(f"AUTO_UPDATES_ENABLED={str(auto_updates_enabled if auto_updates_enabled is not None else DEFAULT_CONFIG['AUTO_UPDATES_ENABLED']).lower()}\n")
            f.write(f"CHECK_FREQUENCY={check_frequency if check_frequency is not None else DEFAULT_CONFIG['CHECK_FREQUENCY']}\n")
            f.write(f"EXTENSIONES_HABILITADAS={str(extensiones_habilitadas if extensiones_habilitadas is not None else DEFAULT_CONFIG['EXTENSIONES_HABILITADAS']).lower()}\n")
            f.write(f"FIRST_BOOT={str(first_boot if first_boot is not None else DEFAULT_CONFIG['FIRST_BOOT']).lower()}\n")
            f.write(f"LAST_UPDATE_CHECK={last_update_check if last_update_check is not None else DEFAULT_CONFIG['LAST_UPDATE_CHECK']}\n")
            f.write(f"STORED_VERSION={stored_version.strip() if stored_version is not None else DEFAULT_CONFIG['STORED_VERSION']}\n")
        print("Archivo de configuraci�n creado con valores por defecto.")
        return
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
        subprocess.run(sed_replace("STORED_VERSION", stored_version.strip()), shell=True)
    print("Configuraci�n guardada.")

# ========================================
# FUNCIONES DE SUBPROCESOS Y EJECUCI�N
# ========================================
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

def apply_updates_py(callback_line):
    return ejecutar_comando_captura("rpm-ostree upgrade", callback_line)

# Funci�n actualizada para el rebase:
def check_silverblue_version_py(callback_line):
    if os.path.isfile(LATEST_RELEASE_FILE):
        with open(LATEST_RELEASE_FILE) as f:
            latest_release = f.read().strip()
    else:
        latest_release = ""
    
    # Intentamos extraer un n�mero de versi�n (por ejemplo, "41") usando regex.
    extracted_version = None
    if latest_release:
        m = re.search(r'/(\d+)/', latest_release)
        if m:
            extracted_version = m.group(1)
    
    # Obtener la versi�n actual del sistema desde /etc/os-release.
    current_version = ""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("VERSION_ID="):
                    current_version = line.split("=")[1].strip().strip('"')
                    break
    except Exception as e:
        callback_line(f"Error al obtener la versi�n actual de Fedora: {e}")
    
    config = read_config()
    stored_version = config.get("STORED_VERSION", "").strip()
    
    # Se procede con el rebase solo si:
    # 1. latest_release existe y es distinta a stored_version.
    # 2. Si se pudo extraer un n�mero de versi�n y �ste coincide con current_version, NO se hace rebase.
    # 3. Si no se pudo extraer un n�mero (imagen personalizada) o el n�mero extra�do es distinto, se hace rebase.
    if latest_release and latest_release != stored_version:
        if extracted_version is not None:
            if extracted_version == current_version:
                callback_line("No hay nuevas versiones de Silverblue disponibles.")
                return
        callback_line(f"Aplicando rebase a la imagen: {latest_release}")
        rcode = ejecutar_comando_captura(f"rpm-ostree rebase {latest_release}", callback_line)
        if rcode == 0:
            callback_line(f"Rebase completado a la imagen: {latest_release}")
            write_config(stored_version=latest_release)
        else:
            callback_line(f"Error al aplicar rebase a {latest_release}.")
    else:
        callback_line("No hay nuevas versiones de Silverblue disponibles.")

def ensure_toolbox_exists(callback_line=None):
    try:
        output = subprocess.check_output("toolbox list", shell=True, text=True)
        if "treeossecure" not in output:
            if callback_line:
                callback_line("Contenedor 'treeossecure' no encontrado. Cre�ndolo autom�ticamente...")
            subprocess.run("podman pull --quiet registry.fedoraproject.org/fedora-toolbox", shell=True, check=True)
            subprocess.run("echo y | toolbox create -c treeossecure --image fedora-toolbox", shell=True, check=True)
            if callback_line:
                callback_line("Contenedor 'treeossecure' creado exitosamente.")
    except subprocess.CalledProcessError as e:
        if callback_line:
            callback_line(f"Error al verificar/crear contenedor: {e}")

# ========================================
# CLASE DE LA VENTANA PRINCIPAL
# ========================================
class ControlPanelWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("TreeOS Control Panel")
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.changing_theme = False

        # Se muestra un mensaje si no se encuentra el icono.
        if not os.path.isfile(APP_ICON):
            print(f"Icono no encontrado: {APP_ICON}")

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

        self.toggle_traditional = Gtk.ToggleButton()
        vbox_traditional = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        img_traditional_path = os.path.join(BASE_DIR, "traditional.png")
        if os.path.isfile(img_traditional_path):
            img_traditional = Gtk.Image.new_from_file(img_traditional_path)
            img_traditional.set_pixel_size(SMALL_IMAGE_SIZE)
            vbox_traditional.append(img_traditional)
        label_traditional = Gtk.Label(label="Traditional")
        vbox_traditional.append(label_traditional)
        self.toggle_traditional.set_child(vbox_traditional)
        self.toggle_traditional.connect("toggled", self.on_traditional_toggled)
        theme_box.append(self.toggle_traditional)

        self.toggle_modern = Gtk.ToggleButton()
        vbox_modern = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        img_modern_path = os.path.join(BASE_DIR, "modern.png")
        if os.path.isfile(img_modern_path):
            img_modern = Gtk.Image.new_from_file(img_modern_path)
            img_modern.set_pixel_size(SMALL_IMAGE_SIZE)
            vbox_modern.append(img_modern)
        label_modern = Gtk.Label(label="Modern")
        vbox_modern.append(label_modern)
        self.toggle_modern.set_child(vbox_modern)
        self.toggle_modern.connect("toggled", self.on_modern_toggled)
        theme_box.append(self.toggle_modern)

        box.append(theme_frame)

        wallpaper_frame = Gtk.Frame(label="Fondos Oficiales de TreeOS")
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
            if not os.path.isfile(wallpaper_path):
                continue
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

        more_options_btn = Gtk.Button(label="Para m�s opciones de apariencia")
        more_options_btn.connect("clicked", lambda w: subprocess.Popen("gnome-control-center background", shell=True))
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
        comando = (
            "gnome-extensions disable dash-to-dock@micxgx.gmail.com || true && "
            "gnome-extensions enable blur-my-shell@aunetx || true && "
            "gnome-extensions enable dash-to-panel@jderose9.github.com || true"
        )
        threading.Thread(target=ejecutar_comando_captura, args=(comando, None), daemon=True).start()

    def activar_modern(self):
        comando = (
            "gnome-extensions disable dash-to-panel@jderose9.github.com || true && "
            "gnome-extensions enable blur-my-shell@aunetx || true && "
            "gnome-extensions enable dash-to-dock@micxgx.gmail.com || true"
        )
        threading.Thread(target=ejecutar_comando_captura, args=(comando, None), daemon=True).start()

    def seleccionar_fondo(self, button, wallpaper_path):
        comando = f"gsettings set org.gnome.desktop.background picture-uri 'file://{wallpaper_path}'"
        threading.Thread(target=ejecutar_comando_captura, args=(comando, None), daemon=True).start()

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
        self.freq_combo.append("daily", "Diariamente")
        self.freq_combo.append("weekly", "Semanalmente")
        self.freq_combo.append("monthly", "Mensualmente")
        config = read_config()
        config_frequency = config.get("CHECK_FREQUENCY", "daily")
        self.freq_combo.set_active_id(config_frequency)

        def on_freq_changed(combo):
            active_id = combo.get_active_id() or "daily"
            write_config(check_frequency=active_id)

        self.freq_combo.connect("changed", on_freq_changed)
        freq_box.append(self.freq_combo)
        box.append(freq_box)

        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        auto_label = Gtk.Label(label="Actualizaciones Autom�ticas:")
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
        self.btn_update_now.connect("clicked", self.on_actualizar_sistema)
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

    def on_actualizar_sistema(self, button):
        if os.path.exists(LOCK_FILE):
            self.append_details_text("�Ya se est� ejecutando una actualizaci�n! Espere a que finalice.")
            return
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        self.btn_update_now.set_sensitive(False)
        self.spinner.start()
        self.img_complete.set_visible(False)
        self.clear_details_text()
        self.append_details_text("Iniciando actualizaci�n manual...")
        t = threading.Thread(target=self.procesar_actualacion, daemon=True)
        t.start()

    def procesar_actualacion(self):
        try:
            apply_updates_py(self.append_details_text)
            check_silverblue_version_py(self.append_details_text)
            self.append_details_text("Actualizaci�n manual completada.")
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

    def build_treeos_ayuda_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=MARGIN)
        header = Gtk.Label()
        header.set_markup("<span size='xx-large' weight='bold'>TreeOS Ayuda</span>")
        header.set_margin_bottom(MARGIN)
        box.append(header)
        guide_text = ("TreeOS es una plataforma innovadora que combina la familiaridad de Windows "
                      "con la flexibilidad de Linux. Utilice esta secci�n para aprender a usar TreeOS "
                      "y sacar el m�ximo provecho de sus funcionalidades.")
        guide_label = Gtk.Label(label=guide_text)
        guide_label.set_wrap(True)
        box.append(guide_label)
        manual_btn = Gtk.Button(label="Abrir Manual de Usuario")
        manual_btn.connect("clicked", self.abrir_manual)
        box.append(manual_btn)
        self.stack.add_titled(box, "TreeOS Ayuda", "TreeOS Ayuda")

    def abrir_manual(self, button):
        if os.path.isfile(MANUAL_FILE):
            subprocess.Popen(f"xdg-open '{MANUAL_FILE}'", shell=True)
        else:
            print("No se encontr� el manual en:", MANUAL_FILE)

    def build_treeos_secure_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=MARGIN)
        header = Gtk.Label()
        header.set_markup("<span size='xx-large' weight='bold'>TreeOS Secure</span>")
        header.set_margin_bottom(MARGIN)
        box.append(header)
        desc = Gtk.Label(label="Instala r�pidamente herramientas de desarrollo dentro del toolbox treeossecure:")
        desc.set_margin_bottom(MARGIN)
        box.append(desc)
        toolbox_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=MARGIN)
        self.btn_pycharm = Gtk.Button(label=self.get_app_button_label("pycharm"))
        self.btn_pycharm.connect("clicked", self.on_toggle_app, "pycharm")
        toolbox_buttons.append(self.btn_pycharm)
        self.btn_vscode = Gtk.Button(label=self.get_app_button_label("vscode"))
        self.btn_vscode.connect("clicked", self.on_toggle_app, "vscode")
        toolbox_buttons.append(self.btn_vscode)
        self.btn_anaconda = Gtk.Button(label=self.get_app_button_label("anaconda"))
        self.btn_anaconda.connect("clicked", self.on_toggle_app, "anaconda")
        toolbox_buttons.append(self.btn_anaconda)
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
        restore_btn = Gtk.Button(label="Restaurar TreeOS Secure")
        restore_btn.connect("clicked", self.on_restaurar_treeossecure)
        box.append(restore_btn)
        self.stack.add_titled(box, "TreeOS Secure", "TreeOS Secure")

    def get_app_button_label(self, app_key):
        if is_app_installed(app_key):
            return "Desinstalar " + APPS_DESKTOP[app_key]['name']
        else:
            return "Instalar " + APPS_DESKTOP[app_key]['name']

    def update_app_button_label(self, app_key):
        label = self.get_app_button_label(app_key)
        if app_key == "pycharm":
            self.btn_pycharm.set_label(label)
        elif app_key == "vscode":
            self.btn_vscode.set_label(label)
        elif app_key == "anaconda":
            self.btn_anaconda.set_label(label)

    def on_toggle_app(self, button, app_key):
        button.set_sensitive(False)
        if is_app_installed(app_key):
            t = threading.Thread(target=self.desinstalar_app_background, args=(app_key, button), daemon=True)
            t.start()
        else:
            t = threading.Thread(target=self.instalar_app_background, args=(app_key, button), daemon=True)
            t.start()

    def desinstalar_app_background(self, app_key, btn):
        GLib.idle_add(self.secure_spinner.start)
        GLib.idle_add(self.secure_img_complete.set_visible, False)
        self.clear_secure_details_text()
        self.append_secure_details_text("Verificando contenedor 'treeossecure' para desinstalaci�n...")
        ensure_toolbox_exists(self.append_secure_details_text)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if app_key == "pycharm":
            script_file = "uninstall_pycharm.sh"
        elif app_key == "vscode":
            script_file = "uninstall_vscode.sh"
        elif app_key == "anaconda":
            script_file = "uninstall_anaconda.sh"
        else:
            script_file = ""
        if script_file:
            script_path = os.path.join(script_dir, script_file)
            uninstall_cmd = f"toolbox run --container treeossecure bash -c 'bash {script_path}'"
        else:
            uninstall_cmd = ""
        if uninstall_cmd:
            self.append_secure_details_text(f"Iniciando desinstalaci�n de {APPS_DESKTOP[app_key]['name']}...")
            ejecutar_comando_captura(uninstall_cmd, self.append_secure_details_text)
            self.append_secure_details_text(f"Desinstalaci�n de {APPS_DESKTOP[app_key]['name']} completada.")
        else:
            self.append_secure_details_text("Error: no se defini� comando para desinstalar la app.")
        data = APPS_DESKTOP[app_key]
        desktop_path = os.path.expanduser(f"~/.local/share/applications/{data['desktop_file']}")
        if os.path.exists(desktop_path):
            try:
                os.remove(desktop_path)
                self.append_secure_details_text(f"Se elimin� el archivo {desktop_path}.")
            except Exception as e:
                self.append_secure_details_text(f"Error al eliminar el archivo {desktop_path}: {e}")
        else:
            self.append_secure_details_text("No se encontr� el archivo de escritorio para eliminar.")
        GLib.idle_add(self.mostrar_secure_imagen_completa)
        GLib.idle_add(self.update_app_button_label, app_key)
        GLib.idle_add(btn.set_sensitive, True)

    def instalar_app_background(self, app_key, btn):
        GLib.idle_add(self.secure_spinner.start)
        GLib.idle_add(self.secure_img_complete.set_visible, False)
        self.clear_secure_details_text()
        self.append_secure_details_text("Verificando contenedor 'treeossecure' para instalaci�n...")
        ensure_toolbox_exists(self.append_secure_details_text)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if app_key == "pycharm":
            script_file = "install_pycharm.sh"
        elif app_key == "vscode":
            script_file = "install_vscode.sh"
        elif app_key == "anaconda":
            script_file = "install_anaconda.sh"
        else:
            script_file = ""
        if script_file:
            script_path = os.path.join(script_dir, script_file)
            install_cmd = f"toolbox run --container treeossecure bash -c 'bash {script_path}'"
        else:
            install_cmd = ""
        if install_cmd:
            self.append_secure_details_text(f"Iniciando instalaci�n de {APPS_DESKTOP[app_key]['name']}...")
            ejecutar_comando_captura(install_cmd, self.append_secure_details_text)
            self.append_secure_details_text(f"Instalaci�n de {APPS_DESKTOP[app_key]['name']} completada.")
            # NOTA: Se elimina la creaci�n del archivo .desktop desde Python,
            # ya que el script .sh correspondiente lo crea con el icono adecuado.
        else:
            self.append_secure_details_text("Error: no se defini� comando para instalar la app.")
        GLib.idle_add(self.mostrar_secure_imagen_completa)
        GLib.idle_add(self.update_app_button_label, app_key)
        GLib.idle_add(btn.set_sensitive, True)

    def on_secure_details_clicked(self, button):
        visible = not self.secure_details_scrolled.get_visible()
        self.secure_details_scrolled.set_visible(visible)
        button.set_label("Ocultar Progreso" if visible else "Ver Progreso")

    def abrir_terminal_toolbox(self, button):
        t = threading.Thread(target=self.abrir_terminal_thread, daemon=True)
        t.start()

    def abrir_terminal_thread(self):
        ensure_toolbox_exists()
        try:
            anaconda_desktop = os.path.expanduser("~/.local/share/applications/anaconda-treeossecure.desktop")
            if os.path.exists(anaconda_desktop):
                subprocess.Popen("ptyxis -- toolbox run --container treeossecure conda activate basenv", shell=True)
            else:
                subprocess.Popen("ptyxis -- toolbox enter treeossecure", shell=True)
        except Exception as e:
            print(f"Error al abrir la terminal en toolbox: {e}")

    def on_restaurar_treeossecure(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="�Est�s seguro que desea restaurar TreeOS Secure?\nEsto eliminar� el contenedor toolbox 'treeossecure'."
        )
        dialog.connect("response", self.on_restore_response)
        dialog.present()

    def on_restore_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            try:
                output = subprocess.check_output("toolbox list", shell=True, text=True)
                if "treeossecure" not in output:
                    self.append_secure_details_text("No se encontr� el contenedor 'treeossecure'.")
                else:
                    result = subprocess.run("toolbox rm -f treeossecure", shell=True, capture_output=True, text=True)
                    if result.returncode == 0:
                        self.append_secure_details_text("TreeOS Secure ha sido restaurado (toolbox eliminado).")
                    else:
                        self.append_secure_details_text(f"Error al restaurar TreeOS Secure: {result.stderr}")
            except subprocess.CalledProcessError as e:
                self.append_secure_details_text(f"Error al verificar contenedor: {e}")
        dialog.destroy()

    def clear_secure_details_text(self):
        buffer = self.secure_details_textview.get_buffer()
        buffer.set_text("")

    def _append_secure_details_text_idle(self, line):
        buffer = self.secure_details_textview.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, line + "\n")

    def append_secure_details_text(self, line):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        GLib.idle_add(self._append_secure_details_text_idle, f"[{now}] {line}")

    def mostrar_secure_imagen_completa(self):
        self.secure_spinner.stop()
        self.secure_img_complete.set_visible(True)

    def update_app_button_label(self, app_key):
        label = self.get_app_button_label(app_key)
        if app_key == "pycharm":
            self.btn_pycharm.set_label(label)
        elif app_key == "vscode":
            self.btn_vscode.set_label(label)
        elif app_key == "anaconda":
            self.btn_anaconda.set_label(label)

    def get_app_button_label(self, app_key):
        if is_app_installed(app_key):
            return "Desinstalar " + APPS_DESKTOP[app_key]['name']
        else:
            return "Instalar " + APPS_DESKTOP[app_key]['name']

class Aplicacion(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.treeoscontrol.app")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        window = ControlPanelWindow(app)
        window.present()

if __name__ == "__main__":
    instance_lock_file = "/tmp/treeos_control_instance.lock"
    lock_file = open(instance_lock_file, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("Otra instancia de TreeOS Control Panel ya est� corriendo.")
        sys.exit(0)
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR, exist_ok=True)
    app = Aplicacion()
    app.run()
