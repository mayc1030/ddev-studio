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
from ddev_studio.core.docker_monitor import list_external_containers, stop_all_external_containers
from ddev_studio.core.ssl_tools import check_ssl_health


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

        # 5. Stop External Containers
        btn_stop_ext = Gtk.Button()
        b_sext = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_sext.pack_start(Gtk.Image.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_sext.pack_start(Gtk.Label(label="Detener Contenedores Externos (Docker)"), False, False, 0)
        btn_stop_ext.add(b_sext)
        btn_stop_ext.set_tooltip_text("Detener contenedores Docker que no pertenecen a DDEV (bases de datos independientes, microservicios, etc.)")
        btn_stop_ext.connect("clicked", self.on_stop_external_containers)
        grid.attach(btn_stop_ext, 0, 2, 1, 1)

        # 6. Stop Everything (DDEV + External)
        btn_stop_all_docker = Gtk.Button()
        b_sall = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_sall.pack_start(Gtk.Image.new_from_icon_name("process-stop-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_sall.pack_start(Gtk.Label(label="Detener TODO en Docker (DDEV + Externos)"), False, False, 0)
        btn_stop_all_docker.add(b_sall)
        btn_stop_all_docker.set_tooltip_text("Detener todos los proyectos DDEV y además todos los contenedores Docker externos activos")
        btn_stop_all_docker.connect("clicked", self.on_stop_everything)
        grid.attach(btn_stop_all_docker, 1, 2, 1, 1)

        # 7. Diagnóstico y Certificados SSL (mkcert)
        btn_ssl_diag = Gtk.Button()
        b_ssl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_ssl.pack_start(Gtk.Image.new_from_icon_name("channel-secure-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_ssl.pack_start(Gtk.Label(label="Diagnóstico y Certificados SSL (mkcert / HTTPS)"), False, False, 0)
        btn_ssl_diag.add(b_ssl)
        btn_ssl_diag.set_tooltip_text("Verificar y reparar la confianza SSL de Chrome, Chromium y Firefox para dominios locales")
        btn_ssl_diag.connect("clicked", self.on_open_ssl_diag)
        grid.attach(btn_ssl_diag, 0, 3, 2, 1)

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

    def on_open_ssl_diag(self, widget=None):
        """Abre el diálogo modal de diagnóstico y reparación de certificados SSL."""
        from ddev_studio.ui.dialogs.ssl_diag import SSLDiagDialog
        dlg = SSLDiagDialog(self.main_app)
        dlg.run()
        dlg.destroy()
        self.update_system_info()

    def update_system_info(self):
        """Consulta en segundo plano las versiones instaladas de DDEV, Docker y estado SSL."""
        def task():
            try:
                v = subprocess.run(["ddev", "--version"], capture_output=True, text=True).stdout.strip()
                dock = subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.strip()
                ssl_h = check_ssl_health()
                if ssl_h["healthy"]:
                    ssl_str = "<span foreground='green'>✅ Confiables en Chrome/Firefox (mkcert + certutil)</span>"
                elif not ssl_h["mkcert_installed"]:
                    ssl_str = "<span foreground='red'>❌ mkcert no encontrado en PATH</span>"
                else:
                    ssl_str = "<span foreground='#d97706'>⚠️ Requiere libnss3-tools (certutil)</span>"

                info_text = (
                    f"• <b>DDEV:</b> {v}\n"
                    f"• <b>Docker:</b> {dock}\n"
                    f"• <b>Certificados SSL (HTTPS):</b> {ssl_str}\n"
                    f"• <b>Directorio predeterminado:</b> {DEFAULT_SITES_DIR}"
                )
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

    def on_stop_external_containers(self, widget=None):
        """Detiene contenedores Docker independientes o externos tras confirmación del usuario."""
        ext_list = list_external_containers()
        if not ext_list:
            dialog = Gtk.MessageDialog(
                transient_for=self.main_app,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="No hay contenedores externos activos"
            )
            dialog.format_secondary_text("No se detectaron contenedores Docker externos ejecutándose actualmente.")
            dialog.run()
            dialog.destroy()
            return

        names_preview = "\n".join([f"• {c['name']} ({c['id'][:12]})" for c in ext_list[:8]])
        if len(ext_list) > 8:
            names_preview += f"\n... y {len(ext_list) - 8} más."

        confirm = Gtk.MessageDialog(
            transient_for=self.main_app,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"¿Confirmas detener {len(ext_list)} contenedor(es) externo(s)?"
        )
        confirm.format_secondary_text(
            f"Se detendrán los siguientes contenedores Docker independientes:\n\n{names_preview}\n\n"
            f"Nota: Esto no afectará a los proyectos DDEV."
        )
        c_resp = confirm.run()
        confirm.destroy()

        if c_resp != Gtk.ResponseType.OK:
            return

        dialog = ProgressDialog(self.main_app, title="Deteniendo Contenedores Docker Externos")
        dialog.set_status("Deteniendo contenedores independientes...")

        def task():
            def log(t):
                GLib.idle_add(dialog.append_log, t)

            log(f"🐳 Iniciando detención de {len(ext_list)} contenedores externos...\n")
            stopped_cnt, stopped_names = stop_all_external_containers(ext_list)
            for name in stopped_names:
                log(f"  ✓ Detenido: {name}\n")

            msg = f"Se detuvieron {stopped_cnt} de {len(ext_list)} contenedor(es) externo(s)."
            GLib.idle_add(dialog.finish, stopped_cnt > 0, msg)
            if hasattr(self, "docker_monitor_view"):
                GLib.idle_add(self.docker_monitor_view.refresh_now)

        threading.Thread(target=task, daemon=True).start()

    def on_stop_everything(self, widget=None):
        """Detiene tanto todos los proyectos DDEV como todos los contenedores Docker externos."""
        ext_list = list_external_containers()
        ext_count = len(ext_list)

        confirm = Gtk.MessageDialog(
            transient_for=self.main_app,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="¿Confirmas detener TODO en Docker?"
        )
        confirm.format_secondary_text(
            "Esta acción ejecutará 'ddev poweroff' para apagar todos los proyectos DDEV "
            f"y además detendrá los {ext_count} contenedor(es) Docker externos activos.\n\n"
            "Todos los servicios web y bases de datos en Docker serán detenidos."
        )
        c_resp = confirm.run()
        confirm.destroy()

        if c_resp != Gtk.ResponseType.OK:
            return

        dialog = ProgressDialog(self.main_app, title="Deteniendo Todo en Docker")
        dialog.set_status("Ejecutando ddev poweroff y deteniendo contenedores externos...")

        def task():
            def log(t):
                GLib.idle_add(dialog.append_log, t)

            log("🛑 1. Deteniendo proyectos DDEV (ddev poweroff)...\n")
            p = subprocess.Popen(["ddev", "poweroff"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(p.stdout.readline, ''):
                log(line)
            p.stdout.close()
            p.wait()

            log(f"\n🐳 2. Deteniendo {ext_count} contenedor(es) externos...\n")
            stopped_cnt, stopped_names = stop_all_external_containers(ext_list)
            for name in stopped_names:
                log(f"  ✓ Detenido: {name}\n")

            msg = f"DDEV apagado y {stopped_cnt} contenedor(es) externos detenidos correctamente."
            GLib.idle_add(dialog.finish, True, msg)
            if self.main_app:
                GLib.idle_add(self.main_app.refresh_projects)
            if hasattr(self, "docker_monitor_view"):
                GLib.idle_add(self.docker_monitor_view.refresh_now)

        threading.Thread(target=task, daemon=True).start()
