# -*- coding: utf-8 -*-
"""
Vista de Herramientas Globales y Estado del Sistema para DDEV Studio.
"""

import subprocess
import threading
import webbrowser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ddev_studio.constants import DEFAULT_SITES_DIR
from ddev_studio.ui.dialogs.progress import ProgressDialog
from ddev_studio.ui.views.docker_monitor import DockerMonitorView


class GlobalToolsView(Gtk.ScrolledWindow):
    """
    Pestaña de herramientas administrativas globales (poweroff, start -a, clean, traefik)
    y monitor de recursos Docker integrado.
    """
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(16)
        box.set_margin_bottom(20)
        self.add(box)

        lbl_title = Gtk.Label()
        lbl_title.set_markup("<b>Herramientas Globales de DDEV</b>")
        lbl_title.set_halign(Gtk.Align.START)
        box.pack_start(lbl_title, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)
        box.pack_start(grid, False, False, 0)

        # 1. Poweroff all
        btn_stop_all = Gtk.Button()
        b_stop = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_stop.pack_start(Gtk.Image.new_from_icon_name("system-shutdown-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_stop.pack_start(Gtk.Label(label="Detener Todos los Proyectos (Poweroff)"), False, False, 0)
        btn_stop_all.add(b_stop)
        btn_stop_all.connect("clicked", self.on_global_poweroff)
        grid.attach(btn_stop_all, 0, 0, 1, 1)

        # 2. Start all
        btn_start_all = Gtk.Button()
        b_start = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_start.pack_start(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_start.pack_start(Gtk.Label(label="Iniciar Todos los Proyectos"), False, False, 0)
        btn_start_all.add(b_start)
        btn_start_all.connect("clicked", self.on_global_start_all)
        grid.attach(btn_start_all, 1, 0, 1, 1)

        # 3. Clean
        btn_clean = Gtk.Button()
        b_clean = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_clean.pack_start(Gtk.Image.new_from_icon_name("edit-clear-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_clean.pack_start(Gtk.Label(label="Limpiar Caché e Imágenes (ddev clean)"), False, False, 0)
        btn_clean.add(b_clean)
        btn_clean.connect("clicked", self.on_clean_ddev)
        grid.attach(btn_clean, 0, 1, 1, 1)

        # 4. Traefik Router
        btn_router = Gtk.Button()
        b_router = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_router.pack_start(Gtk.Image.new_from_icon_name("network-server-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_router.pack_start(Gtk.Label(label="Abrir Panel Traefik Router"), False, False, 0)
        btn_router.add(b_router)
        btn_router.connect("clicked", lambda b: webbrowser.open("http://127.0.0.1:10999"))
        grid.attach(btn_router, 1, 1, 1, 1)

        # Separador y Monitor de Recursos Docker en Vivo
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(sep, False, False, 4)

        self.docker_monitor_view = DockerMonitorView(self.main_app)
        # Exponer al main_app para que pueda pausar/reanudar el polling en switch-page
        if self.main_app:
            self.main_app.docker_monitor_view = self.docker_monitor_view
        box.pack_start(self.docker_monitor_view, True, True, 0)

        # Estado básico del sistema
        info_frame = Gtk.Frame(label=" Versiones del Entorno ")
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_margin_start(10)
        info_box.set_margin_end(10)
        info_box.set_margin_top(8)
        info_box.set_margin_bottom(8)

        self.lbl_system_info = Gtk.Label()
        self.lbl_system_info.set_halign(Gtk.Align.START)
        self.lbl_system_info.set_line_wrap(True)
        info_box.pack_start(self.lbl_system_info, False, False, 0)
        info_frame.add(info_box)
        box.pack_start(info_frame, False, False, 0)

        self.update_system_info()

    def update_system_info(self):
        """Consulta en segundo plano las versiones instaladas de DDEV y Docker."""
        def task():
            try:
                v = subprocess.run(["ddev", "--version"], capture_output=True, text=True).stdout.strip()
                dock = subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.strip()
                info_text = f"• <b>DDEV:</b> {v}\n• <b>Docker:</b> {dock}\n• <b>Directorio predeterminado:</b> {DEFAULT_SITES_DIR}"
            except Exception as e:
                info_text = f"Error obteniendo estado: {e}"
            GLib.idle_add(lambda: self.lbl_system_info.set_markup(info_text))
        threading.Thread(target=task, daemon=True).start()

    def on_global_poweroff(self, widget=None):
        """Detiene todos los contenedores DDEV globalmente."""
        dialog = ProgressDialog(self.main_app, title="Deteniendo DDEV")
        dialog.set_status("Deteniendo todos los contenedores...")
        def task():
            p = subprocess.Popen(["ddev", "poweroff"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(p.stdout.readline, ''):
                GLib.idle_add(dialog.append_log, line)
            p.stdout.close()
            p.wait()
            GLib.idle_add(dialog.finish, p.returncode == 0, "Todos los proyectos se detuvieron correctamente")
            if self.main_app:
                GLib.idle_add(self.main_app.refresh_projects)
        threading.Thread(target=task, daemon=True).start()

    def on_global_start_all(self, widget=None):
        """Inicia todos los proyectos DDEV configurados."""
        dialog = ProgressDialog(self.main_app, title="Iniciando Proyectos")
        dialog.set_status("Iniciando todos los proyectos...")
        def task():
            p = subprocess.Popen(["ddev", "start", "-a"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(p.stdout.readline, ''):
                GLib.idle_add(dialog.append_log, line)
            p.stdout.close()
            p.wait()
            GLib.idle_add(dialog.finish, p.returncode == 0, "Proyectos iniciados")
            if self.main_app:
                GLib.idle_add(self.main_app.refresh_projects)
        threading.Thread(target=task, daemon=True).start()

    def on_clean_ddev(self, widget=None):
        """Ejecuta ddev clean para purgar imágenes y cachés."""
        dialog = ProgressDialog(self.main_app, title="Limpiando DDEV")
        dialog.set_status("Ejecutando ddev clean...")
        def task():
            p = subprocess.Popen(["ddev", "clean", "-y"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(p.stdout.readline, ''):
                GLib.idle_add(dialog.append_log, line)
            p.stdout.close()
            p.wait()
            GLib.idle_add(dialog.finish, p.returncode == 0, "Limpieza completada")
            if self.main_app:
                GLib.idle_add(self.main_app.refresh_projects)
        threading.Thread(target=task, daemon=True).start()
