# -*- coding: utf-8 -*-
"""
Vista de inspección y detalles técnicos profundos del proyecto (servicios, runtimes, base de datos, Xdebug, logs).
"""

import json
import os
import subprocess
import threading
import webbrowser
from datetime import datetime
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from ddev_studio.core.detector import inspect_project_stack, detect_sqlite_database
from ddev_studio.core.ci_templates import detect_git_repo, detect_existing_workflows
from ddev_studio.ui.helpers import load_icon
from ddev_studio.ui.dialogs.progress import ProgressDialog
from ddev_studio.ui.dialogs.db_containers import DBContainersDialog
from ddev_studio.ui.dialogs.ci_dialog import CIDialog


class ProjectDetailsView(Gtk.Box):
    def __init__(self, main_app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_app = main_app
        self.proj = {}
        self.proj_name = ""
        self.base_dir = ""
        self.raw_data = {}
        
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(10)
        self.set_margin_bottom(14)
        
        # 0. Top Navigation Bar
        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        nav_bar.get_style_context().add_class("nav-bar-box")
        
        self.btn_back = Gtk.Button()
        btn_back_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_back_box.pack_start(Gtk.Image.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        btn_back_box.pack_start(Gtk.Label(label="Volver a Mis Proyectos"), False, False, 0)
        self.btn_back.add(btn_back_box)
        self.btn_back.get_style_context().add_class("btn-back")
        self.btn_back.connect("clicked", lambda b: self.main_app.show_projects_list())
        nav_bar.pack_start(self.btn_back, False, False, 0)
        
        self.lbl_breadcrumb = Gtk.Label()
        self.lbl_breadcrumb.set_markup("<span color='#94a3b8'>Mis Proyectos / </span><b>Detalles del Proyecto</b>")
        self.lbl_breadcrumb.set_halign(Gtk.Align.START)
        nav_bar.pack_start(self.lbl_breadcrumb, True, True, 0)
        
        btn_refresh = Gtk.Button()
        btn_refresh.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        btn_refresh.set_tooltip_text("Refrescar detalles y estado en vivo")
        btn_refresh.connect("clicked", lambda b: self.refresh_details())
        nav_bar.pack_start(btn_refresh, False, False, 0)
        
        self.pack_start(nav_bar, False, False, 0)
        
        # Scrolled content
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_vexpand(True)
        self.pack_start(self.scrolled, True, True, 0)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.content_box.set_margin_top(4)
        self.content_box.set_margin_end(6)
        self.scrolled.add(self.content_box)

    def get_project_db_addons(self, approot="", services=None):
        addons = []
        if not approot or not os.path.exists(approot):
            return addons
        ddev_dir = os.path.join(approot, ".ddev")
        services = services or {}
        
        # 1. DBeaver in Docker
        if os.path.exists(os.path.join(ddev_dir, "docker-compose.cloudbeaver.yaml")):
            cb_svc = services.get("cloudbeaver", {})
            cb_url = cb_svc.get("https_url") if isinstance(cb_svc, dict) else None
            addons.append({"id": "cloudbeaver", "name": "DBeaver", "port": 8979, "url": cb_url, "icon": "drive-harddisk-symbolic"})
            
        # 2. phpMyAdmin
        if os.path.exists(os.path.join(ddev_dir, "docker-compose.phpmyadmin.yaml")):
            pma_svc = services.get("phpmyadmin", {})
            pma_url = pma_svc.get("https_url") if isinstance(pma_svc, dict) else None
            addons.append({"id": "phpmyadmin", "name": "phpMyAdmin", "port": 8037, "url": pma_url, "icon": "web-browser-symbolic"})
            
        # 3. Adminer (Default DDEV port 9101 HTTPS / 9100 HTTP)
        if os.path.exists(os.path.join(ddev_dir, "docker-compose.adminer.yaml")):
            adm_svc = services.get("adminer", {})
            adm_url = adm_svc.get("https_url") if isinstance(adm_svc, dict) else None
            addons.append({"id": "adminer", "name": "Adminer", "port": 9101, "url": adm_url, "icon": "web-browser-symbolic"})
            
        return addons

    def show_db_containers_dialog(self, approot, proj_name, primary_url):
        dialog = DBContainersDialog(self, approot, proj_name, primary_url)
        dialog.run()
        dialog.destroy()

    def show_ci_dialog(self, approot, proj_name, tech_type):
        dialog = CIDialog(self.main_app, approot, proj_name, tech_type)
        dialog.run()
        self.render_project_details(self.raw_data)

    def export_db(self, approot, proj_name, target_file):
        dialog = ProgressDialog(self.main_app, title=f"Exportar Base de Datos: {proj_name}")
        dialog.set_status(f"Exportando base de datos a {os.path.basename(target_file)}...")
        
        def task():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t)
                
                log(f"📦 Ejecutando 'ddev export-db --file={target_file}'...\n")
                p = subprocess.Popen(["ddev", "export-db", f"--file={target_file}"], cwd=approot, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in iter(p.stdout.readline, ''):
                    log(line)
                p.stdout.close()
                p.wait()
                
                success = (p.returncode == 0)
                msg = f"Base de datos exportada con éxito en:\n{target_file}" if success else "Error al exportar la base de datos"
                GLib.idle_add(dialog.finish, success, msg, "", os.path.dirname(target_file))
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {ex}", "", approot)
                
        threading.Thread(target=task, daemon=True).start()

    def import_db(self, approot, proj_name, source_file):
        dialog = ProgressDialog(self.main_app, title=f"Importar Base de Datos: {proj_name}")
        dialog.set_status(f"Importando {os.path.basename(source_file)} en {proj_name}...")
        
        def task():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t)
                
                log(f"📥 Ejecutando 'ddev import-db --file={source_file}'...\n")
                p = subprocess.Popen(["ddev", "import-db", f"--file={source_file}"], cwd=approot, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in iter(p.stdout.readline, ''):
                    log(line)
                p.stdout.close()
                p.wait()
                
                success = (p.returncode == 0)
                msg = f"Base de datos importada con éxito desde:\n{source_file}" if success else "Error al importar la base de datos"
                GLib.idle_add(dialog.finish, success, msg, "", approot)
                GLib.idle_add(self.refresh_details)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {ex}", "", approot)
                
        threading.Thread(target=task, daemon=True).start()

    def on_export_db_clicked(self, approot, pname):
        chooser = Gtk.FileChooserDialog(
            title=f"Exportar Base de Datos ({pname})",
            parent=self.main_app,
            action=Gtk.FileChooserAction.SAVE
        )
        chooser.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        chooser.add_button("Exportar", Gtk.ResponseType.OK)
        chooser.set_do_overwrite_confirmation(True)
        chooser.set_modal(True)
        chooser.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{pname}_db_{now_str}.sql.gz"
        chooser.set_current_name(default_filename)
        
        downloads_dir = os.path.expanduser("~/Descargas")
        if not os.path.exists(downloads_dir):
            downloads_dir = os.path.expanduser("~/Downloads")
        if os.path.exists(downloads_dir):
            chooser.set_current_folder(downloads_dir)
        else:
            chooser.set_current_folder(os.path.expanduser("~"))
            
        filter_sql_gz = Gtk.FileFilter()
        filter_sql_gz.set_name("SQL Comprimido (*.sql.gz)")
        filter_sql_gz.add_pattern("*.sql.gz")
        chooser.add_filter(filter_sql_gz)
        
        filter_sql = Gtk.FileFilter()
        filter_sql.set_name("Archivos SQL (*.sql)")
        filter_sql.add_pattern("*.sql")
        chooser.add_filter(filter_sql)
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("Todos los archivos (*.*)")
        filter_all.add_pattern("*")
        chooser.add_filter(filter_all)
        
        chooser.present()
        resp = chooser.run()
        target_path = chooser.get_filename()
        chooser.destroy()
        
        if resp == Gtk.ResponseType.OK and target_path:
            self.export_db(approot, pname, target_path)

    def on_import_db_clicked(self, approot, pname):
        chooser = Gtk.FileChooserDialog(
            title=f"Importar Base de Datos en {pname}",
            parent=self.main_app,
            action=Gtk.FileChooserAction.OPEN
        )
        chooser.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        chooser.add_button("Importar", Gtk.ResponseType.OK)
        chooser.set_modal(True)
        chooser.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        
        downloads_dir = os.path.expanduser("~/Descargas")
        if not os.path.exists(downloads_dir):
            downloads_dir = os.path.expanduser("~/Downloads")
        if os.path.exists(downloads_dir):
            chooser.set_current_folder(downloads_dir)
        else:
            chooser.set_current_folder(os.path.expanduser("~"))
            
        filter_db = Gtk.FileFilter()
        filter_db.set_name("Respaldos de Base de Datos (*.sql, *.sql.gz, *.tar.gz, *.zip)")
        filter_db.add_pattern("*.sql")
        filter_db.add_pattern("*.sql.gz")
        filter_db.add_pattern("*.tar.gz")
        filter_db.add_pattern("*.zip")
        chooser.add_filter(filter_db)
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("Todos los archivos (*.*)")
        filter_all.add_pattern("*")
        chooser.add_filter(filter_all)
        
        chooser.present()
        resp = chooser.run()
        source_path = chooser.get_filename()
        chooser.destroy()
        
        if resp == Gtk.ResponseType.OK and source_path:
            confirm = Gtk.MessageDialog(
                transient_for=self.main_app,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=f"¿Confirmas la importación en '{pname}'?"
            )
            confirm.format_secondary_text(f"Se importará el archivo:\n{os.path.basename(source_path)}\n\n⚠️ ADVERTENCIA: Esta acción sobreescribirá las tablas existentes en la base de datos de '{pname}'.")
            c_resp = confirm.run()
            confirm.destroy()
            if c_resp == Gtk.ResponseType.OK:
                self.import_db(approot, pname, source_path)

    def load_project_details(self, proj):
        self.proj = proj
        self.proj_name = proj.get("name", "")
        self.base_dir = proj.get("approot", "")
        self.lbl_breadcrumb.set_markup(f"<span color='#94a3b8'>Mis Proyectos / </span><b>{self.proj_name}</b> <span color='#0284c7'>[Detalles y Servicios]</span>")
        self.refresh_details()

    def refresh_details(self):
        for child in self.content_box.get_children():
            self.content_box.remove(child)
            
        loader_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        loader_box.set_halign(Gtk.Align.CENTER)
        loader_box.set_valign(Gtk.Align.CENTER)
        loader_box.set_margin_top(80)
        loader_box.set_margin_bottom(80)
        
        spinner = Gtk.Spinner()
        spinner.get_style_context().add_class("big-spinner")
        spinner.set_size_request(48, 48)
        spinner.start()
        loader_box.pack_start(spinner, False, False, 0)
        
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span size='large' weight='600'>Cargando detalles...</span>")
        lbl_title.set_halign(Gtk.Align.CENTER)
        loader_box.pack_start(lbl_title, False, False, 0)
        
        lbl_proj = Gtk.Label()
        lbl_proj.set_markup(f"<span color='#38bdf8' size='medium'><b>{self.proj_name}</b></span>")
        lbl_proj.set_halign(Gtk.Align.CENTER)
        loader_box.pack_start(lbl_proj, False, False, 0)
        
        self.content_box.pack_start(loader_box, True, True, 0)
        self.content_box.show_all()
        
        def fetch():
            try:
                res = subprocess.run(["ddev", "describe", "-j", self.proj_name], capture_output=True, text=True, timeout=15)
                raw_data = None
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("{") and "raw" in line:
                        try:
                            parsed = json.loads(line)
                            if "raw" in parsed:
                                raw_data = parsed["raw"]
                                break
                        except Exception:
                            pass
                if not raw_data:
                    raw_data = self.proj
            except Exception:
                raw_data = self.proj
                
            # Query real-time dynamic Xdebug status in background thread
            approot = raw_data.get("approot", self.base_dir)
            if approot and os.path.exists(approot):
                try:
                    xd_res = subprocess.run(["ddev", "xdebug", "status"], cwd=approot, capture_output=True, text=True, timeout=4)
                    xd_out = xd_res.stdout.lower()
                    if "xdebug enabled" in xd_out or ("enabled" in xd_out and "disabled" not in xd_out):
                        raw_data["is_xdebug_live"] = True
                    elif "xdebug disabled" in xd_out or "disabled" in xd_out:
                        raw_data["is_xdebug_live"] = False
                except Exception:
                    pass
                    
            GLib.idle_add(self.render_details_ui, raw_data)
            
        threading.Thread(target=fetch, daemon=True).start()

    def render_details_ui(self, data):
        for child in self.content_box.get_children():
            self.content_box.remove(child)
            
        self.raw_data = data or {}
        pname = self.raw_data.get("name", self.proj_name)
        status = self.raw_data.get("status", "stopped").lower()
        is_running = ("running" in status or "ok" in status)
        approot = self.raw_data.get("approot", self.base_dir)
        php_ver = self.raw_data.get("php_version", "N/A")
        node_ver = self.raw_data.get("nodejs_version", "N/A")
        docroot = self.raw_data.get("docroot", "")
        webserver = self.raw_data.get("webserver_type", "nginx-fpm")
        primary_url = self.raw_data.get("primary_url", f"https://{pname}.ddev.site")
        mailpit_url = self.raw_data.get("mailpit_https_url") or self.raw_data.get("mailpit_url") or f"https://{pname}.ddev.site:8026"
        services = self.raw_data.get("services", {}) or {}
        
        # Accurate Full-Stack Inspection
        tech_type, has_db, is_php, is_python, is_js, is_static = inspect_project_stack(approot, self.raw_data, self.proj)
        is_xdebug = self.raw_data.get("is_xdebug_live", self.raw_data.get("xdebug_enabled", False)) if is_php else False
        
        # 1. Header Overview Card
        header_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        header_card.get_style_context().add_class("option-highlight-box")
        
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        # Find icon based on accurate tech_type
        icon_file = "ddev.svg"
        if "next" in tech_type:
            icon_file = "nextjs.svg"
        else:
            for fw_cand in ["drupal", "wordpress", "laravel", "django", "flask", "angular", "react", "vue", "symfony", "python", "php", "node"]:
                if fw_cand in tech_type:
                    icon_file = f"{fw_cand}.svg"
                    break
        pix = load_icon(icon_file, 36)
        if pix:
            top_row.pack_start(Gtk.Image.new_from_pixbuf(pix), False, False, 0)
            
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        t_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_name = Gtk.Label()
        lbl_name.set_markup(f"<big><b>{pname}</b></big>")
        t_row.pack_start(lbl_name, False, False, 0)
        
        lbl_status = Gtk.Label(label="EN EJECUCIÓN" if is_running else "DETENIDO")
        lbl_status.get_style_context().add_class("badge")
        lbl_status.get_style_context().add_class("badge-running" if is_running else "badge-stopped")
        t_row.pack_start(lbl_status, False, False, 0)
        
        lbl_type = Gtk.Label(label=tech_type.upper())
        lbl_type.get_style_context().add_class("badge")
        lbl_type.get_style_context().add_class("badge-type")
        t_row.pack_start(lbl_type, False, False, 0)
        
        title_box.pack_start(t_row, False, False, 0)
        
        lbl_loc = Gtk.Label()
        lbl_loc.set_markup(f"<small><span color='#94a3b8'>📁 Ubicación:</span> <tt>{approot}</tt></small>")
        lbl_loc.set_halign(Gtk.Align.START)
        title_box.pack_start(lbl_loc, False, False, 0)
        
        top_row.pack_start(title_box, True, True, 0)
        header_card.pack_start(top_row, False, False, 0)
        
        # Primary Quick Actions Row
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_row.set_margin_top(4)
        
        if is_running:
            btn_stop = Gtk.Button()
            b_st = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_st.pack_start(Gtk.Image.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_st.pack_start(Gtk.Label(label="Detener DDEV"), False, False, 0)
            btn_stop.add(b_st)
            btn_stop.get_style_context().add_class("btn-stop")
            btn_stop.connect("clicked", lambda b: self.execute_action_and_refresh("stop"))
            actions_row.pack_start(btn_stop, False, False, 0)
            
            btn_restart = Gtk.Button()
            b_rs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_rs.pack_start(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_rs.pack_start(Gtk.Label(label="Reiniciar DDEV"), False, False, 0)
            btn_restart.add(b_rs)
            btn_restart.connect("clicked", lambda b: self.execute_action_and_refresh("restart"))
            actions_row.pack_start(btn_restart, False, False, 0)
            
            btn_open_web = Gtk.Button()
            b_ow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_ow.pack_start(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_ow.pack_start(Gtk.Label(label="Abrir Web"), False, False, 0)
            btn_open_web.add(b_ow)
            btn_open_web.get_style_context().add_class("btn-primary")
            btn_open_web.connect("clicked", lambda b, u=primary_url: webbrowser.open(u))
            actions_row.pack_start(btn_open_web, False, False, 0)
            
            btn_mailpit = Gtk.Button()
            b_mp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_mp.pack_start(Gtk.Image.new_from_icon_name("mail-unread-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_mp.pack_start(Gtk.Label(label="Mailpit"), False, False, 0)
            btn_mailpit.add(b_mp)
            btn_mailpit.set_tooltip_text("Bandeja de correos de prueba Mailpit")
            btn_mailpit.connect("clicked", lambda b, u=mailpit_url: webbrowser.open(u))
            actions_row.pack_start(btn_mailpit, False, False, 0)
        else:
            btn_start = Gtk.Button()
            b_start = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_start.pack_start(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_start.pack_start(Gtk.Label(label="Iniciar DDEV"), False, False, 0)
            btn_start.add(b_start)
            btn_start.get_style_context().add_class("btn-start")
            btn_start.connect("clicked", lambda b: self.execute_action_and_refresh("start"))
            actions_row.pack_start(btn_start, False, False, 0)
            
        btn_folder = Gtk.Button()
        b_f = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_f.pack_start(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_f.pack_start(Gtk.Label(label="Carpeta"), False, False, 0)
        btn_folder.add(b_f)
        btn_folder.connect("clicked", lambda b: subprocess.Popen(["xdg-open", approot]))
        actions_row.pack_start(btn_folder, False, False, 0)
        
        btn_term = Gtk.Button()
        b_t = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_t.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_t.pack_start(Gtk.Label(label="Terminal"), False, False, 0)
        btn_term.add(b_t)
        btn_term.connect("clicked", lambda b: self.main_app.open_terminal(approot))
        actions_row.pack_start(btn_term, False, False, 0)
        
        header_card.pack_start(actions_row, False, False, 0)
        self.content_box.pack_start(header_card, False, False, 0)
        
        # 2. Database Card (Docker Database or SQLite)
        sqlite_info = detect_sqlite_database(approot)
        if sqlite_info:
            db_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            db_card.get_style_context().add_class("project-card")
            
            db_title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            db_title_row.pack_start(Gtk.Image.new_from_icon_name("drive-harddisk-symbolic", Gtk.IconSize.MENU), False, False, 0)
            lbl_db_title = Gtk.Label()
            lbl_db_title.set_markup("<b>Base de Datos &amp; Archivo Local</b>")
            db_title_row.pack_start(lbl_db_title, False, False, 0)
            
            lbl_badge_sql = Gtk.Label(label="SQLITE (ARCHIVO LOCAL)")
            lbl_badge_sql.get_style_context().add_class("badge")
            lbl_badge_sql.get_style_context().add_class("badge-running")
            db_title_row.pack_start(lbl_badge_sql, False, False, 0)
            db_card.pack_start(db_title_row, False, False, 0)
            
            grid_db = Gtk.Grid()
            grid_db.set_column_spacing(20)
            grid_db.set_row_spacing(6)
            
            grid_db.attach(Gtk.Label(label="Motor:", halign=Gtk.Align.END), 0, 0, 1, 1)
            grid_db.attach(Gtk.Label(label="<b>SQLite 3</b> (Sin contenedor Docker - 0 MB RAM)", use_markup=True, halign=Gtk.Align.START), 1, 0, 1, 1)
            
            grid_db.attach(Gtk.Label(label="Archivo:", halign=Gtk.Align.END), 0, 1, 1, 1)
            grid_db.attach(Gtk.Label(label=f"<tt><b>{sqlite_info['rel_path']}</b></tt>", use_markup=True, halign=Gtk.Align.START), 1, 1, 1, 1)
            
            grid_db.attach(Gtk.Label(label="Tamaño:", halign=Gtk.Align.END), 2, 0, 1, 1)
            grid_db.attach(Gtk.Label(label=f"<b>{sqlite_info['size_human']}</b>", use_markup=True, halign=Gtk.Align.START), 3, 0, 1, 1)
            
            db_card.pack_start(grid_db, False, False, 0)
            
            db_row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            db_row1.set_margin_top(6)
            
            btn_open_file = Gtk.Button()
            b_of = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_of.pack_start(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_of.pack_start(Gtk.Label(label="Abrir Carpeta de Base de Datos"), False, False, 0)
            btn_open_file.add(b_of)
            file_target = sqlite_info["full_path"] if sqlite_info["full_path"] else approot
            folder_target = os.path.dirname(file_target) if os.path.isfile(file_target) else approot
            btn_open_file.connect("clicked", lambda b, p=folder_target: subprocess.Popen(["xdg-open", p]))
            db_row1.pack_start(btn_open_file, False, False, 0)
            
            db_card.pack_start(db_row1, False, False, 0)
            self.content_box.pack_start(db_card, False, False, 0)
            
        elif has_db:
            db_info = self.raw_data.get("dbinfo") or {}
            db_type = self.raw_data.get("database_type", self.raw_data.get("db_type", "mariadb"))
            db_ver = self.raw_data.get("database_version", "10.11")
            db_name = db_info.get("dbname", "db")
            db_user = db_info.get("username", "db")
            db_pass = db_info.get("password", "db")
            db_in_port = db_info.get("dbPort", "3306")
            db_pub_port = db_info.get("published_port", -1)
            ext_port_str = str(db_pub_port) if (db_pub_port and db_pub_port > 0) else f"{db_in_port} (Automático)"
            
            db_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            db_card.get_style_context().add_class("project-card")
            
            db_title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            db_title_row.pack_start(Gtk.Image.new_from_icon_name("drive-harddisk-symbolic", Gtk.IconSize.MENU), False, False, 0)
            lbl_db_title = Gtk.Label()
            lbl_db_title.set_markup("<b>Base de Datos &amp; Conexión Externa</b>")
            db_title_row.pack_start(lbl_db_title, False, False, 0)
            db_card.pack_start(db_title_row, False, False, 0)
            
            grid_db = Gtk.Grid()
            grid_db.set_column_spacing(20)
            grid_db.set_row_spacing(6)
            
            grid_db.attach(Gtk.Label(label="Motor:", halign=Gtk.Align.END), 0, 0, 1, 1)
            grid_db.attach(Gtk.Label(label=f"<b>{db_type.upper()} {db_ver}</b>", use_markup=True, halign=Gtk.Align.START), 1, 0, 1, 1)
            
            grid_db.attach(Gtk.Label(label="Host Local:", halign=Gtk.Align.END), 0, 1, 1, 1)
            grid_db.attach(Gtk.Label(label="<b>127.0.0.1</b> (o <tt>localhost</tt>)", use_markup=True, halign=Gtk.Align.START), 1, 1, 1, 1)
            
            grid_db.attach(Gtk.Label(label="Puerto Externo:", halign=Gtk.Align.END), 0, 2, 1, 1)
            grid_db.attach(Gtk.Label(label=f"<b>{ext_port_str}</b>", use_markup=True, halign=Gtk.Align.START), 1, 2, 1, 1)
            
            grid_db.attach(Gtk.Label(label="Base de datos:", halign=Gtk.Align.END), 2, 0, 1, 1)
            grid_db.attach(Gtk.Label(label=f"<tt><b>{db_name}</b></tt>", use_markup=True, halign=Gtk.Align.START), 3, 0, 1, 1)
            
            grid_db.attach(Gtk.Label(label="Usuario:", halign=Gtk.Align.END), 2, 1, 1, 1)
            grid_db.attach(Gtk.Label(label=f"<tt><b>{db_user}</b></tt> (o <tt>root</tt>)", use_markup=True, halign=Gtk.Align.START), 3, 1, 1, 1)
            
            grid_db.attach(Gtk.Label(label="Contraseña:", halign=Gtk.Align.END), 2, 2, 1, 1)
            grid_db.attach(Gtk.Label(label=f"<tt><b>{db_pass}</b></tt> (o <tt>root</tt>)", use_markup=True, halign=Gtk.Align.START), 3, 2, 1, 1)
            
            db_card.pack_start(grid_db, False, False, 0)
            
            # DB Action buttons
            db_btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            db_btn_box.set_margin_top(6)
            
            db_row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            raw_db_creds = f"Host: 127.0.0.1\nPort: {ext_port_str}\nDatabase: {db_name}\nUsername: {db_user}\nPassword: {db_pass}\nURL: {db_type}://{db_user}:{db_pass}@127.0.0.1:{ext_port_str}/{db_name}"
            
            btn_copy_db = Gtk.Button()
            b_c = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_c.pack_start(Gtk.Image.new_from_icon_name("edit-copy-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_c.pack_start(Gtk.Label(label="Copiar Credenciales"), False, False, 0)
            btn_copy_db.add(b_c)
            btn_copy_db.connect("clicked", lambda b, text=raw_db_creds: self.copy_to_clipboard(text, "Credenciales copiadas al portapapeles"))
            db_row1.pack_start(btn_copy_db, False, False, 0)
            
            if is_running:
                btn_export_db = Gtk.Button()
                b_exp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                b_exp.pack_start(Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.MENU), False, False, 0)
                b_exp.pack_start(Gtk.Label(label="Exportar Base de Datos (.sql.gz)"), False, False, 0)
                btn_export_db.add(b_exp)
                btn_export_db.set_tooltip_text("Exportar un volcado completo de la base de datos (ddev export-db)")
                btn_export_db.connect("clicked", lambda b: self.on_export_db_clicked(approot, pname))
                db_row1.pack_start(btn_export_db, False, False, 0)
                
                btn_import_db = Gtk.Button()
                b_imp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                b_imp.pack_start(Gtk.Image.new_from_icon_name("document-open-symbolic", Gtk.IconSize.MENU), False, False, 0)
                b_imp.pack_start(Gtk.Label(label="Importar Base de Datos (.sql)"), False, False, 0)
                btn_import_db.add(b_imp)
                btn_import_db.set_tooltip_text("Importar un archivo de volcado a la base de datos (ddev import-db)")
                btn_import_db.connect("clicked", lambda b: self.on_import_db_clicked(approot, pname))
                db_row1.pack_start(btn_import_db, False, False, 0)
                
                btn_launch_db = Gtk.Button()
                b_ld = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                b_ld.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.MENU), False, False, 0)
                b_ld.pack_start(Gtk.Label(label="Consola CLI (ddev mysql)"), False, False, 0)
                btn_launch_db.add(b_ld)
                btn_launch_db.connect("clicked", lambda b: self.main_app.open_terminal(approot, "ddev mysql" if "postgres" not in db_type else "ddev psql"))
                db_row1.pack_start(btn_launch_db, False, False, 0)
                
                db_btn_box.pack_start(db_row1, False, False, 0)
                
                # Row 2: Visual Managers in Containers
                db_row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                active_addons = self.get_project_db_addons(approot, services)
                if active_addons:
                    for ad in active_addons:
                        btn_ad = Gtk.Button()
                        b_ad = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        b_ad.pack_start(Gtk.Image.new_from_icon_name(ad.get("icon", "web-browser-symbolic"), Gtk.IconSize.MENU), False, False, 0)
                        b_ad.pack_start(Gtk.Label(label=f"Abrir {ad['name']}"), False, False, 0)
                        btn_ad.add(b_ad)
                        btn_ad.get_style_context().add_class("btn-primary" if "DBeaver" in ad['name'] else "btn-quick")
                        target_port = ad["port"]
                        ad_url = ad.get("url") or f"{primary_url}:{target_port}"
                        btn_ad.set_tooltip_text(f"Abrir interfaz web de {ad['name']} ({ad_url})")
                        btn_ad.connect("clicked", lambda b, u=ad_url: webbrowser.open(u))
                        db_row2.pack_start(btn_ad, False, False, 0)
                        
                btn_manage_db = Gtk.Button()
                b_mdb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                b_mdb.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.MENU), False, False, 0)
                b_label_txt = "Gestores en Docker (phpMyAdmin / Adminer / DBeaver)" if not active_addons else "Gestionar Gestores Web"
                b_mdb.pack_start(Gtk.Label(label=b_label_txt), False, False, 0)
                btn_manage_db.add(b_mdb)
                if not active_addons:
                    btn_manage_db.get_style_context().add_class("btn-primary")
                btn_manage_db.set_tooltip_text("Habilitar o gestionar phpMyAdmin, Adminer o DBeaver en contenedores Docker")
                btn_manage_db.connect("clicked", lambda b: self.show_db_containers_dialog(approot, pname, primary_url))
                db_row2.pack_start(btn_manage_db, False, False, 0)
                
                db_btn_box.pack_start(db_row2, False, False, 0)
            else:
                btn_manage_db = Gtk.Button()
                b_mdb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                b_mdb.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.MENU), False, False, 0)
                b_mdb.pack_start(Gtk.Label(label="Gestores en Docker (Configurar)"), False, False, 0)
                btn_manage_db.add(b_mdb)
                btn_manage_db.set_tooltip_text("Habilitar o deshabilitar phpMyAdmin, Adminer o DBeaver")
                btn_manage_db.connect("clicked", lambda b: self.show_db_containers_dialog(approot, pname, primary_url))
                db_row1.pack_start(btn_manage_db, False, False, 0)
                
                lbl_hint = Gtk.Label()
                lbl_hint.set_markup("<small><span color='#94a3b8'>💡 Inicia el proyecto para exportar/importar, abrir la consola SQL o acceder a los gestores web.</span></small>")
                lbl_hint.set_halign(Gtk.Align.START)
                
                db_btn_box.pack_start(db_row1, False, False, 0)
                db_btn_box.pack_start(lbl_hint, False, False, 0)
                
            db_card.pack_start(db_btn_box, False, False, 0)
            self.content_box.pack_start(db_card, False, False, 0)
            
        # 3. Environment & Runtime Card (Webserver, PHP / Python / Node.js / Xdebug)
        env_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        env_card.get_style_context().add_class("project-card")
        
        env_title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        env_title_row.pack_start(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_env_title = Gtk.Label()
        lbl_env_title.set_markup("<b>Servidor Web, Runtimes &amp; Depuración</b>")
        env_title_row.pack_start(lbl_env_title, False, False, 0)
        env_card.pack_start(env_title_row, False, False, 0)
        
        grid_env = Gtk.Grid()
        grid_env.set_column_spacing(20)
        grid_env.set_row_spacing(6)
        
        # Col 1: Webserver & Docroot (Universal)
        grid_env.attach(Gtk.Label(label="Servidor Web:", halign=Gtk.Align.END), 0, 0, 1, 1)
        grid_env.attach(Gtk.Label(label=f"<b>{webserver}</b>", use_markup=True, halign=Gtk.Align.START), 1, 0, 1, 1)
        
        grid_env.attach(Gtk.Label(label="Directorio Web (Docroot):", halign=Gtk.Align.END), 0, 1, 1, 1)
        grid_env.attach(Gtk.Label(label=f"<tt><b>{docroot if docroot else '.'}</b></tt>", use_markup=True, halign=Gtk.Align.START), 1, 1, 1, 1)
        
        # Col 2: Framework-specific runtimes
        if is_php:
            grid_env.attach(Gtk.Label(label="Versión de PHP:", halign=Gtk.Align.END), 2, 0, 1, 1)
            grid_env.attach(Gtk.Label(label=f"<b>PHP {php_ver}</b>", use_markup=True, halign=Gtk.Align.START), 3, 0, 1, 1)
            
            grid_env.attach(Gtk.Label(label="Node.js (Herramientas):", halign=Gtk.Align.END), 2, 1, 1, 1)
            node_txt = f"<b>v{node_ver}</b>" if (node_ver and node_ver != "N/A") else "<i>No configurado</i>"
            grid_env.attach(Gtk.Label(label=node_txt, use_markup=True, halign=Gtk.Align.START), 3, 1, 1, 1)
            
            grid_env.attach(Gtk.Label(label="Xdebug (PHP):", halign=Gtk.Align.END), 0, 2, 1, 1)
            xdbg_st = "<span color='#10b981'><b>ACTIVO (Enabled)</b></span>" if is_xdebug else "<span color='#94a3b8'>Desactivado</span>"
            grid_env.attach(Gtk.Label(label=xdbg_st, use_markup=True, halign=Gtk.Align.START), 1, 2, 1, 1)
            
        elif is_python:
            grid_env.attach(Gtk.Label(label="Entorno de Ejecución:", halign=Gtk.Align.END), 2, 0, 1, 1)
            grid_env.attach(Gtk.Label(label=f"<b>Python 3 (WSGI/ASGI)</b>", use_markup=True, halign=Gtk.Align.START), 3, 0, 1, 1)
            
            grid_env.attach(Gtk.Label(label="Node.js (Frontend):", halign=Gtk.Align.END), 2, 1, 1, 1)
            node_txt = f"<b>v{node_ver}</b>" if (node_ver and node_ver != "N/A") else "<i>No requerido</i>"
            grid_env.attach(Gtk.Label(label=node_txt, use_markup=True, halign=Gtk.Align.START), 3, 1, 1, 1)
            
        elif is_js:
            grid_env.attach(Gtk.Label(label="Runtime Principal:", halign=Gtk.Align.END), 2, 0, 1, 1)
            node_txt = f"<b>Node.js v{node_ver}</b>" if (node_ver and node_ver != "N/A") else "<b>Node.js (LTS)</b>"
            grid_env.attach(Gtk.Label(label=node_txt, use_markup=True, halign=Gtk.Align.START), 3, 0, 1, 1)
            
            grid_env.attach(Gtk.Label(label="Tipo de Aplicación:", halign=Gtk.Align.END), 2, 1, 1, 1)
            grid_env.attach(Gtk.Label(label=f"<b>{tech_type.capitalize()} SPA / Frontend</b>", use_markup=True, halign=Gtk.Align.START), 3, 1, 1, 1)
            
        else: # static / html
            grid_env.attach(Gtk.Label(label="Tipo de Proyecto:", halign=Gtk.Align.END), 2, 0, 1, 1)
            grid_env.attach(Gtk.Label(label="<b>HTML / Estático</b>", use_markup=True, halign=Gtk.Align.START), 3, 0, 1, 1)
            
        env_card.pack_start(grid_env, False, False, 0)
        
        # Contextual Action buttons (Only when running)
        if is_running:
            env_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            env_btn_row.set_margin_top(4)
            
            if is_php:
                btn_xdebug = Gtk.Button()
                b_xd = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                b_xd.pack_start(Gtk.Image.new_from_icon_name("system-run-symbolic", Gtk.IconSize.MENU), False, False, 0)
                lbl_xd_btn = "Desactivar Xdebug (ddev xdebug off)" if is_xdebug else "Activar Xdebug (ddev xdebug on)"
                b_xd.pack_start(Gtk.Label(label=lbl_xd_btn), False, False, 0)
                btn_xdebug.add(b_xd)
                btn_xdebug.get_style_context().add_class("btn-primary" if not is_xdebug else "btn-quick")
                btn_xdebug.connect("clicked", lambda b: self.toggle_xdebug(not is_xdebug))
                env_btn_row.pack_start(btn_xdebug, False, False, 0)
                
            elif is_python:
                btn_py = Gtk.Button()
                b_py = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                b_py.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.MENU), False, False, 0)
                b_py.pack_start(Gtk.Label(label="Consola Python (ddev exec python)"), False, False, 0)
                btn_py.add(b_py)
                btn_py.connect("clicked", lambda b: self.main_app.open_terminal(approot, "ddev exec python"))
                env_btn_row.pack_start(btn_py, False, False, 0)
                
            elif is_js:
                btn_npm = Gtk.Button()
                b_npm = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                b_npm.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.MENU), False, False, 0)
                b_npm.pack_start(Gtk.Label(label=f"Consola NPM / {tech_type.capitalize()} (ddev npm)"), False, False, 0)
                btn_npm.add(b_npm)
                btn_npm.connect("clicked", lambda b: self.main_app.open_terminal(approot, "ddev npm"))
                env_btn_row.pack_start(btn_npm, False, False, 0)
                
            if env_btn_row.get_children():
                env_card.pack_start(env_btn_row, False, False, 0)
                
        self.content_box.pack_start(env_card, False, False, 0)
        
        # 4. Registered URLs and Domains Card
        urls_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        urls_card.get_style_context().add_class("project-card")
        
        url_title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        url_title_row.pack_start(Gtk.Image.new_from_icon_name("network-server-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_u_title = Gtk.Label()
        lbl_u_title.set_markup("<b>Dominios &amp; URLs Registradas en este Proyecto</b>")
        url_title_row.pack_start(lbl_u_title, False, False, 0)
        urls_card.pack_start(url_title_row, False, False, 0)
        
        grid_urls = Gtk.Grid()
        grid_urls.set_column_spacing(16)
        grid_urls.set_row_spacing(6)
        
        https_urls = self.raw_data.get("httpsURLs") or []
        http_urls = self.raw_data.get("httpURLs") or []
        all_urls = self.raw_data.get("urls") or []
        
        seen_hosts = set()
        clean_urls = []
        
        for u in https_urls + all_urls:
            if u and not u.startswith("http://127.0.0.1") and not u.startswith("https://127.0.0.1"):
                host = u.replace("https://", "").replace("http://", "").rstrip("/")
                if host and host not in seen_hosts:
                    seen_hosts.add(host)
                    clean_urls.append(u if u.startswith("https://") else f"https://{host}")
                    
        for u in http_urls:
            if u and not u.startswith("http://127.0.0.1") and not u.startswith("https://127.0.0.1"):
                host = u.replace("http://", "").rstrip("/")
                if host and host not in seen_hosts:
                    seen_hosts.add(host)
                    clean_urls.append(u)
                
        if not clean_urls:
            clean_urls = [primary_url]
            
        for idx, u in enumerate(clean_urls):
            lbl_dot = Gtk.Label(label="•")
            grid_urls.attach(lbl_dot, 0, idx, 1, 1)
            
            btn_link = Gtk.LinkButton(uri=u, label=u)
            btn_link.set_halign(Gtk.Align.START)
            grid_urls.attach(btn_link, 1, idx, 1, 1)
            
        urls_card.pack_start(grid_urls, False, False, 0)
        self.content_box.pack_start(urls_card, False, False, 0)
        
        # 5. Continuous Integration (GitHub Actions) Card
        ci_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        ci_card.get_style_context().add_class("project-card")
        
        ci_title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ci_title_row.pack_start(Gtk.Image.new_from_icon_name("system-run-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_ci_title = Gtk.Label()
        lbl_ci_title.set_markup("<b>Integración Continua (CI/CD - GitHub Actions)</b>")
        ci_title_row.pack_start(lbl_ci_title, False, False, 0)
        
        git_info = detect_git_repo(approot)
        existing_wfs = detect_existing_workflows(approot)
        
        if existing_wfs:
            lbl_ci_badge = Gtk.Label(label=f"ACTIVO ({len(existing_wfs)} WORKFLOWS)")
            lbl_ci_badge.get_style_context().add_class("badge")
            lbl_ci_badge.get_style_context().add_class("badge-running")
            ci_title_row.pack_start(lbl_ci_badge, False, False, 0)
        else:
            lbl_ci_badge = Gtk.Label(label="SIN CONFIGURAR")
            lbl_ci_badge.get_style_context().add_class("badge")
            ci_title_row.pack_start(lbl_ci_badge, False, False, 0)
            
        ci_card.pack_start(ci_title_row, False, False, 0)
        
        ci_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        if existing_wfs:
            wf_list_str = ", ".join([w["filename"] for w in existing_wfs])
            lbl_wf_info = Gtk.Label()
            lbl_wf_info.set_markup(f"Flujos de trabajo detectados en <tt>.github/workflows/</tt>: <b>{wf_list_str}</b>")
            lbl_wf_info.set_halign(Gtk.Align.START)
            ci_content_box.pack_start(lbl_wf_info, False, False, 0)
        else:
            lbl_wf_info = Gtk.Label()
            lbl_wf_info.set_markup("Automatiza pruebas unitarias, validación de código (linter) y auditoría de seguridad en cada <tt>git push</tt>.")
            lbl_wf_info.set_halign(Gtk.Align.START)
            ci_content_box.pack_start(lbl_wf_info, False, False, 0)
            
        ci_btns_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ci_btns_row.set_margin_top(4)
        
        btn_ci_modal = Gtk.Button()
        b_cim = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_cim.pack_start(Gtk.Image.new_from_icon_name("document-edit-symbolic" if existing_wfs else "list-add-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_cim.pack_start(Gtk.Label(label="Configurar / Generar GitHub Actions" if not existing_wfs else "Gestionar / Regenerar Workflows"), False, False, 0)
        btn_ci_modal.add(b_cim)
        if not existing_wfs:
            btn_ci_modal.get_style_context().add_class("btn-primary")
        else:
            btn_ci_modal.get_style_context().add_class("btn-quick")
        btn_ci_modal.connect("clicked", lambda b, a=approot, p=pname, t=tech_type: self.show_ci_dialog(a, p, t))
        ci_btns_row.pack_start(btn_ci_modal, False, False, 0)
        
        if existing_wfs:
            btn_open_wf = Gtk.Button()
            b_owf = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_owf.pack_start(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_owf.pack_start(Gtk.Label(label="Abrir Carpeta .github"), False, False, 0)
            btn_open_wf.add(b_owf)
            wf_folder = os.path.join(approot, ".github", "workflows")
            btn_open_wf.connect("clicked", lambda b, p=wf_folder: subprocess.Popen(["xdg-open", p]))
            ci_btns_row.pack_start(btn_open_wf, False, False, 0)
            
        if git_info.get("github_url"):
            actions_url = f"{git_info['github_url']}/actions"
            btn_gh = Gtk.Button()
            b_gh = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_gh.pack_start(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_gh.pack_start(Gtk.Label(label="Ver en GitHub Actions"), False, False, 0)
            btn_gh.add(b_gh)
            btn_gh.connect("clicked", lambda b, u=actions_url: webbrowser.open(u))
            ci_btns_row.pack_start(btn_gh, False, False, 0)
            
        ci_content_box.pack_start(ci_btns_row, False, False, 0)
        ci_card.pack_start(ci_content_box, False, False, 0)
        
        self.content_box.pack_start(ci_card, False, False, 0)
        self.content_box.show_all()

    def copy_to_clipboard(self, text, message="Copiado al portapapeles"):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()
        dialog = Gtk.MessageDialog(
            transient_for=self.main_app,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.format_secondary_text(f"Contenido:\n{text}")
        dialog.run()
        dialog.destroy()

    def toggle_xdebug(self, enable):
        pname = self.proj_name
        approot = self.raw_data.get("approot") or self.base_dir or self.proj.get("approot", "")
        cmd = ["ddev", "xdebug", "on"] if enable else ["ddev", "xdebug", "off"]
        dialog = ProgressDialog(self.main_app, title=f"Xdebug: {pname}")
        dialog.set_status(f"Cambiando Xdebug a {'ON (Habilitado)' if enable else 'OFF (Desactivado)'}...")
        
        def task():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t)
                
                log(f"⚡ Ejecutando 'ddev xdebug {'on' if enable else 'off'}'...\n")
                p = subprocess.Popen(cmd, cwd=approot, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in iter(p.stdout.readline, ''):
                    log(line)
                p.stdout.close()
                p.wait()
                
                success = (p.returncode == 0)
                GLib.idle_add(dialog.finish, success, f"Xdebug {'activado con éxito' if enable else 'desactivado con éxito'}")
                GLib.idle_add(self.refresh_details)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {ex}")
                
        threading.Thread(target=task, daemon=True).start()

    def execute_action_and_refresh(self, action):
        p = self.proj
        self.main_app.execute_simple_action(action, p)
        GLib.timeout_add(1500, self.refresh_details)
