# -*- coding: utf-8 -*-
"""
Vista de gestión avanzada para arquitecturas Drupal Multisite (subsitios, Drush contextual, FQDNs, DBs).
"""

import json
import os
import re
import shutil
import subprocess
import threading
import webbrowser
from datetime import datetime
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from ddev_studio.ui.helpers import load_icon, create_icon_menu_item
from ddev_studio.ui.dialogs.progress import ProgressDialog


class SubsitesManagerView(Gtk.Box):
    def __init__(self, main_app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_app = main_app
        self.proj = {}
        self.base_dir = ""
        self.base_name = ""
        self.subsites = []
        
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(10)
        self.set_margin_bottom(14)
        
        # 0. Top Navigation Bar (Back button + Breadcrumb + Quick Refresh)
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
        self.lbl_breadcrumb.set_markup("<span color='#94a3b8'>Mis Proyectos / </span><b>Drupal Multisite</b>")
        self.lbl_breadcrumb.set_halign(Gtk.Align.START)
        nav_bar.pack_start(self.lbl_breadcrumb, True, True, 0)
        
        btn_refresh_top = Gtk.Button()
        btn_refresh_top.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        btn_refresh_top.set_tooltip_text("Refrescar estado y subsitios")
        btn_refresh_top.connect("clicked", lambda b: self.refresh_subsites())
        nav_bar.pack_start(btn_refresh_top, False, False, 0)
        
        self.pack_start(nav_bar, False, False, 0)
        
        # Main scrolled content for Subsites Manager
        scrolled_main = Gtk.ScrolledWindow()
        scrolled_main.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_main.set_vexpand(True)
        self.pack_start(scrolled_main, True, True, 0)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(4)
        content_box.set_margin_end(6)
        scrolled_main.add(content_box)
        
        # 1. Header Box (Project Summary & Controls)
        header_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        header_card.get_style_context().add_class("option-highlight-box")
        
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        pix_dp = load_icon("drupal.svg", 36)
        if pix_dp:
            top_row.pack_start(Gtk.Image.new_from_pixbuf(pix_dp), False, False, 0)
            
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.lbl_header_title = Gtk.Label()
        self.lbl_header_title.set_markup("<b>Proyecto Drupal</b> <span color='#8b5cf6'><b>[DRUPAL MULTISITE]</b></span>")
        self.lbl_header_title.set_halign(Gtk.Align.START)
        title_box.pack_start(self.lbl_header_title, False, False, 0)
        
        self.lbl_header_path = Gtk.Label()
        self.lbl_header_path.set_markup("<small><span color='#94a3b8'>📁 <b>Ubicación:</b> /</span></small>")
        self.lbl_header_path.set_halign(Gtk.Align.START)
        title_box.pack_start(self.lbl_header_path, False, False, 0)
        top_row.pack_start(title_box, True, True, 0)
        
        header_card.pack_start(top_row, False, False, 0)
        
        # Controls row
        ctrl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_base_info = Gtk.Label()
        self.lbl_base_info.set_halign(Gtk.Align.START)
        self.lbl_base_info.set_hexpand(True)
        ctrl_row.pack_start(self.lbl_base_info, True, True, 0)
        
        self.btn_base_start = Gtk.Button()
        b_start_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_start_box.pack_start(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_start_box.pack_start(Gtk.Label(label="Iniciar DDEV"), False, False, 0)
        self.btn_base_start.add(b_start_box)
        self.btn_base_start.get_style_context().add_class("btn-primary")
        self.btn_base_start.connect("clicked", lambda b: self.execute_base_ddev_action("start"))
        ctrl_row.pack_start(self.btn_base_start, False, False, 0)
        
        self.btn_base_stop = Gtk.Button()
        b_stop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_stop_box.pack_start(Gtk.Image.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_stop_box.pack_start(Gtk.Label(label="Detener DDEV"), False, False, 0)
        self.btn_base_stop.add(b_stop_box)
        self.btn_base_stop.connect("clicked", lambda b: self.execute_base_ddev_action("stop"))
        ctrl_row.pack_start(self.btn_base_stop, False, False, 0)
        
        btn_base_composer = Gtk.Button()
        b_comp_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_comp_box.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_comp_box.pack_start(Gtk.Label(label="Composer Install"), False, False, 0)
        btn_base_composer.add(b_comp_box)
        btn_base_composer.set_tooltip_text("Instalar o actualizar dependencias de Composer (Drupal Core y Drush)")
        btn_base_composer.connect("clicked", lambda b: self.execute_base_composer_install())
        ctrl_row.pack_start(btn_base_composer, False, False, 0)
        
        btn_base_details = Gtk.Button()
        b_det_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_det_box.pack_start(Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_det_box.pack_start(Gtk.Label(label="Detalles & Servicios"), False, False, 0)
        btn_base_details.add(b_det_box)
        btn_base_details.get_style_context().add_class("btn-quick")
        btn_base_details.set_tooltip_text("Ver detalles técnicos, base de datos, PHP, Xdebug y servicios de este proyecto")
        btn_base_details.connect("clicked", lambda b: self.open_base_project_details())
        ctrl_row.pack_start(btn_base_details, False, False, 0)
        
        btn_base_folder = Gtk.Button()
        btn_base_folder.add(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON))
        btn_base_folder.set_tooltip_text("Abrir carpeta del proyecto base")
        btn_base_folder.connect("clicked", lambda b: subprocess.Popen(["xdg-open", self.base_dir]))
        ctrl_row.pack_start(btn_base_folder, False, False, 0)
        
        btn_base_term = Gtk.Button()
        btn_base_term.add(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON))
        btn_base_term.set_tooltip_text("Abrir terminal en el proyecto base")
        btn_base_term.connect("clicked", lambda b: self.main_app.open_terminal(self.base_dir))
        ctrl_row.pack_start(btn_base_term, False, False, 0)
        
        header_card.pack_start(ctrl_row, False, False, 0)
        content_box.pack_start(header_card, False, False, 0)
        
        # 2. Provision New Subsite Expander
        self.expander_new = Gtk.Expander(label="➕ Crear / Aprovisionar Nuevo Subsitio en este Proyecto")
        self.expander_new.set_expanded(False)
        
        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        form_box.set_margin_top(8)
        form_box.set_margin_start(12)
        form_box.set_margin_end(12)
        
        grid = Gtk.Grid()
        grid.set_column_spacing(14)
        grid.set_row_spacing(8)
        form_box.pack_start(grid, False, False, 0)
        
        grid.attach(Gtk.Label(label="Nombre / Marca:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.entry_subsite_name = Gtk.Entry()
        self.entry_subsite_name.set_placeholder_text("ej. mikes, corona, alexanderkeiths, millstreet, poker")
        self.entry_subsite_name.set_hexpand(True)
        self.entry_subsite_name.connect("changed", self.on_subsite_input_changed)
        grid.attach(self.entry_subsite_name, 1, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="Perfil de Instalación:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.combo_subsite_profile = Gtk.ComboBoxText()
        self.combo_subsite_profile.append("acquia_cms_minimal", "Acquia CMS Minimal (Recomendado para Acquia)")
        self.combo_subsite_profile.append("minimal", "Minimal (Drupal estándar ligero)")
        self.combo_subsite_profile.append("standard", "Standard (Drupal estándar completo)")
        self.combo_subsite_profile.append("none", "Sin perfil (Solo estructura y base de datos)")
        self.combo_subsite_profile.set_active_id("minimal")
        grid.attach(self.combo_subsite_profile, 1, 1, 1, 1)
        
        self.chk_subsite_auto_install = Gtk.CheckButton(label="Ejecutar instalación automática de Drupal (drush site:install)")
        self.chk_subsite_auto_install.set_active(True)
        grid.attach(self.chk_subsite_auto_install, 1, 2, 1, 1)
        
        self.lbl_subsite_preview = Gtk.Label()
        self.lbl_subsite_preview.set_halign(Gtk.Align.START)
        self.lbl_subsite_preview.set_markup("<small><span color='#94a3b8'>Ingresa un nombre para ver la vista previa de URL y Base de Datos</span></small>")
        grid.attach(self.lbl_subsite_preview, 1, 3, 1, 1)
        
        btn_create = Gtk.Button(label="🚀 Aprovisionar Subsitio en 1 Clic")
        btn_create.get_style_context().add_class("btn-primary")
        btn_create.connect("clicked", self.on_create_subsite_clicked)
        form_box.pack_start(btn_create, False, False, 0)
        
        self.expander_new.add(form_box)
        content_box.pack_start(self.expander_new, False, False, 0)
        
        # 3. Subsites List Header & Container
        list_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_subsites_count = Gtk.Label()
        self.lbl_subsites_count.set_markup("<b>Subsitios Aprovisionados:</b>")
        self.lbl_subsites_count.set_halign(Gtk.Align.START)
        list_header.pack_start(self.lbl_subsites_count, True, True, 0)
        content_box.pack_start(list_header, False, False, 0)
        
        self.subsites_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content_box.pack_start(self.subsites_list_box, False, False, 0)

    def open_base_project_details(self):
        p = self.proj or {"name": self.base_name, "approot": self.base_dir, "type": "drupal9", "status": "running"}
        self.main_app.open_project_details(p)

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

    def show_subsite_details_dialog(self, subsite):
        dialog = Gtk.Dialog(
            title=f"Detalles del Subsitio: {subsite['name']}",
            parent=self.main_app,
            flags=0
        )
        dialog.set_default_size(540, -1)
        dialog.add_button("Cerrar", Gtk.ResponseType.CLOSE)
        
        box = dialog.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.get_style_context().add_class("project-card")
        
        h_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pix_dp = load_icon("drupal.svg", 32)
        if pix_dp:
            h_row.pack_start(Gtk.Image.new_from_pixbuf(pix_dp), False, False, 0)
            
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<big><b>Subsitio: {subsite['name']}</b></big>")
        h_row.pack_start(lbl_title, False, False, 0)
        
        lbl_badge = Gtk.Label(label="MULTISITE")
        lbl_badge.get_style_context().add_class("badge")
        lbl_badge.get_style_context().add_class("badge-multisite")
        h_row.pack_start(lbl_badge, False, False, 0)
        
        card.pack_start(h_row, False, False, 0)
        
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(8)
        grid.set_margin_top(6)
        
        grid.attach(Gtk.Label(label="URL del Subsitio:", halign=Gtk.Align.END), 0, 0, 1, 1)
        lbl_u = Gtk.Label()
        lbl_u.set_markup(f"🌐 <a href='{subsite['url']}'><b>{subsite['url']}</b></a>")
        lbl_u.set_halign(Gtk.Align.START)
        grid.attach(lbl_u, 1, 0, 1, 1)
        
        grid.attach(Gtk.Label(label="Base de Datos:", halign=Gtk.Align.END), 0, 1, 1, 1)
        lbl_db = Gtk.Label()
        lbl_db.set_markup(f"<tt><b>{subsite['db']}</b></tt> (Usuario: <tt>db</tt> / Clave: <tt>db</tt>)")
        lbl_db.set_halign(Gtk.Align.START)
        grid.attach(lbl_db, 1, 1, 1, 1)
        
        grid.attach(Gtk.Label(label="Directorio:", halign=Gtk.Align.END), 0, 2, 1, 1)
        lbl_dir = Gtk.Label()
        lbl_dir.set_markup(f"<small><tt>{subsite['path']}</tt></small>")
        lbl_dir.set_halign(Gtk.Align.START)
        grid.attach(lbl_dir, 1, 2, 1, 1)
        
        card.pack_start(grid, False, False, 0)
        
        btn_box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box1.set_margin_top(8)
        
        raw_db_creds = f"Host: 127.0.0.1\nDatabase: {subsite['db']}\nUsername: db\nPassword: db\nURL: mysql://db:db@127.0.0.1/{subsite['db']}"
        btn_copy = Gtk.Button()
        b_c = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_c.pack_start(Gtk.Image.new_from_icon_name("edit-copy-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_c.pack_start(Gtk.Label(label="Copiar Credenciales"), False, False, 0)
        btn_copy.add(b_c)
        btn_copy.connect("clicked", lambda b: self.copy_to_clipboard(raw_db_creds, f"Credenciales de {subsite['name']} copiadas"))
        btn_box1.pack_start(btn_copy, False, False, 0)
        
        btn_exp = Gtk.Button()
        b_exp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_exp.pack_start(Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_exp.pack_start(Gtk.Label(label="Exportar BD"), False, False, 0)
        btn_exp.add(b_exp)
        btn_exp.set_tooltip_text(f"Exportar base de datos '{subsite['db']}'")
        btn_exp.connect("clicked", lambda b: [dialog.response(Gtk.ResponseType.OK), self.execute_subsite_drush_action("export_db", subsite["name"], subsite["url"], self.base_dir)])
        btn_box1.pack_start(btn_exp, False, False, 0)
        
        btn_imp = Gtk.Button()
        b_imp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_imp.pack_start(Gtk.Image.new_from_icon_name("document-open-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_imp.pack_start(Gtk.Label(label="Importar BD"), False, False, 0)
        btn_imp.add(b_imp)
        btn_imp.set_tooltip_text(f"Importar base de datos en '{subsite['db']}'")
        btn_imp.connect("clicked", lambda b: [dialog.response(Gtk.ResponseType.OK), self.execute_subsite_drush_action("import_db", subsite["name"], subsite["url"], self.base_dir)])
        btn_box1.pack_start(btn_imp, False, False, 0)
        
        btn_cli = Gtk.Button()
        b_cli = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_cli.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_cli.pack_start(Gtk.Label(label="Consola SQL"), False, False, 0)
        btn_cli.add(b_cli)
        btn_cli.set_tooltip_text(f"Abrir consola MySQL en la base de datos '{subsite['db']}'")
        btn_cli.connect("clicked", lambda b: self.main_app.open_terminal(self.base_dir, f"ddev mysql --database={subsite['db']}"))
        btn_box1.pack_start(btn_cli, False, False, 0)
        
        card.pack_start(btn_box1, False, False, 0)
        
        btn_full_details = Gtk.Button()
        b_fd = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_fd.pack_start(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_fd.pack_start(Gtk.Label(label="Ver Detalles y Servicios del Contenedor DDEV Principal"), False, False, 0)
        btn_full_details.add(b_fd)
        btn_full_details.get_style_context().add_class("btn-primary")
        btn_full_details.set_margin_top(6)
        btn_full_details.connect("clicked", lambda b: [dialog.response(Gtk.ResponseType.OK), self.open_base_project_details()])
        card.pack_start(btn_full_details, False, False, 0)
        
        box.pack_start(card, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def load_project(self, proj):
        self.proj = proj
        self.base_name = proj.get("name", "Proyecto Drupal")
        self.base_dir = proj.get("approot", "")
        self.lbl_breadcrumb.set_markup(f"<span color='#94a3b8'>Mis Proyectos / </span><b>{self.base_name}</b> <span color='#8b5cf6'>[Drupal Multisite]</span>")
        self.lbl_header_title.set_markup(f"<big><b>{self.base_name}</b></big> <span color='#8b5cf6'><b>[DRUPAL MULTISITE]</b></span>")
        self.lbl_header_path.set_markup(f"<small><span color='#94a3b8'>📁 <b>Ubicación:</b> {self.base_dir}</span></small>")
        self.entry_subsite_name.set_text("")
        self.expander_new.set_expanded(False)
        self.refresh_subsites()

    def update_ddev_fqdns(self, base_dir, add_subsite=None, remove_subsite=None):
        docroot_dir = "docroot" if os.path.exists(os.path.join(base_dir, "docroot")) else ("web" if os.path.exists(os.path.join(base_dir, "web")) else ".")
        sites_dir = os.path.join(base_dir, docroot_dir, "sites")
        existing_subsites = set()
        if os.path.exists(sites_dir):
            try:
                for entry in os.listdir(sites_dir):
                    full_p = os.path.join(sites_dir, entry)
                    if os.path.isdir(full_p) and entry not in ["default", "g", "settings", "all", "simpletest"]:
                        existing_subsites.add(entry)
            except Exception:
                pass
        if add_subsite:
            existing_subsites.add(add_subsite)
        if remove_subsite and remove_subsite in existing_subsites:
            existing_subsites.remove(remove_subsite)
            
        fqdns = [f"{s}.ddev.site" for s in sorted(existing_subsites)]
        fqdns_arg = ",".join(fqdns)
        subprocess.run(["ddev", "config", f"--additional-fqdns={fqdns_arg}"], cwd=base_dir, capture_output=True)

    def run_subproc(self, cmd, cwd, dialog):
        GLib.idle_add(dialog.append_log, f"$ {' '.join(cmd)}\n")
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(proc.stdout.readline, ''):
            if line:
                GLib.idle_add(dialog.append_log, line)
        proc.stdout.close()
        proc.wait()
        if proc.returncode != 0:
            raise Exception(f"El comando falló con código {proc.returncode}: {' '.join(cmd)}")

    def on_subsite_input_changed(self, entry):
        raw_name = entry.get_text().strip()
        slug = re.sub(r'[^a-zA-Z0-9_-]', '-', raw_name).lower()
        if not slug:
            self.lbl_subsite_preview.set_markup("<small><span color='#94a3b8'>Ingresa un nombre para ver la vista previa</span></small>")
            return
            
        url_preview = f"https://{slug}.ddev.site"
        db_preview = slug
        config_preview = f"config/{slug}"
        has_config = os.path.exists(os.path.join(self.base_dir, "config", slug))
        cfg_badge = f"<span color='#10b981'><b>✓ {config_preview} detectado</b></span>" if has_config else f"<span color='#94a3b8'>{config_preview} (opcional)</span>"
        
        self.lbl_subsite_preview.set_markup(
            f"<small>• <b>URL:</b> <a href='{url_preview}'>{url_preview}</a>  |  "
            f"• <b>Base de Datos:</b> <tt>{db_preview}</tt>  |  "
            f"• <b>Config Split:</b> {cfg_badge}</small>"
        )

    def refresh_subsites(self):
        for child in self.subsites_list_box.get_children():
            self.subsites_list_box.remove(child)
            
        loader_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        loader_box.set_halign(Gtk.Align.CENTER)
        loader_box.set_valign(Gtk.Align.CENTER)
        loader_box.set_margin_top(40)
        loader_box.set_margin_bottom(40)
        
        spinner = Gtk.Spinner()
        spinner.get_style_context().add_class("big-spinner")
        spinner.set_size_request(48, 48)
        spinner.start()
        loader_box.pack_start(spinner, False, False, 0)
        
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span size='large' weight='600'>Cargando subsitios...</span>")
        lbl_title.set_halign(Gtk.Align.CENTER)
        loader_box.pack_start(lbl_title, False, False, 0)
        
        lbl_sub = Gtk.Label()
        lbl_sub.set_markup(f"<span color='#94a3b8' size='medium'>Escaneando entorno de </span><span color='#38bdf8'><b>{self.base_name}</b></span>")
        lbl_sub.set_halign(Gtk.Align.CENTER)
        loader_box.pack_start(lbl_sub, False, False, 0)
        
        self.subsites_list_box.pack_start(loader_box, True, True, 0)
        self.subsites_list_box.show_all()
        
        subsites = []
        docroot_dir = "docroot" if os.path.exists(os.path.join(self.base_dir, "docroot")) else ("web" if os.path.exists(os.path.join(self.base_dir, "web")) else ".")
        sites_dir = os.path.join(self.base_dir, docroot_dir, "sites")
        
        if os.path.exists(sites_dir):
            try:
                for entry in sorted(os.listdir(sites_dir)):
                    full_p = os.path.join(sites_dir, entry)
                    if os.path.isdir(full_p) and entry not in ["default", "g", "settings", "all", "simpletest"]:
                        subsites.append({
                            "name": entry,
                            "path": full_p,
                            "url": f"https://{entry}.ddev.site",
                            "db": entry,
                            "config_exists": os.path.exists(os.path.join(self.base_dir, "config", entry))
                        })
            except Exception:
                pass
                
        def check_status():
            try:
                res = subprocess.run(["ddev", "list", "-j"], capture_output=True, text=True, timeout=10)
                ddev_data = json.loads(res.stdout) if res.stdout else {}
                proj_list = ddev_data.get("raw", [])
                base_proj = next((p for p in proj_list if p.get("name") == self.base_name or p.get("approot") == self.base_dir), None)
            except Exception:
                base_proj = None
            GLib.idle_add(self.update_subsites_ui, subsites, base_proj)
            
        threading.Thread(target=check_status, daemon=True).start()

    def update_subsites_ui(self, subsites, base_proj):
        for child in self.subsites_list_box.get_children():
            self.subsites_list_box.remove(child)
            
        self.subsites = subsites
        if base_proj:
            self.proj = base_proj
            st = base_proj.get("status", "stopped").lower()
            is_run = "running" in st or "ok" in st
            php_v = base_proj.get("php_version", "8.3")
            primary_u = base_proj.get("primary_url", f"https://{self.base_name}.ddev.site")
            st_color = "#10b981" if is_run else "#6b7280"
            st_text = "Activo (Running)" if is_run else "Detenido (Stopped)"
            self.lbl_base_info.set_markup(
                f"• Estado: <span color='{st_color}'><b>{st_text}</b></span> | PHP: {php_v}\n"
                f"• URL Base: <a href='{primary_u}'>{primary_u}</a>"
            )
            self.btn_base_start.set_visible(not is_run)
            self.btn_base_stop.set_visible(is_run)
        else:
            self.lbl_base_info.set_markup(
                f"• Estado: <span color='#6b7280'><b>Detenido / No iniciado</b></span>\n"
                f"• Pulsa <i>'Iniciar DDEV'</i> para activar el contenedor multisite."
            )
            self.btn_base_start.set_visible(True)
            self.btn_base_stop.set_visible(False)
            
        self.lbl_subsites_count.set_markup(f"<b>Subsitios Aprovisionados ({len(subsites)}):</b>")
        
        if not subsites:
            self.expander_new.set_expanded(True)
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty_box.set_margin_top(16)
            empty_box.set_margin_bottom(16)
            icon = Gtk.Image.new_from_icon_name("folder-saved-search-symbolic", Gtk.IconSize.DIALOG)
            empty_box.pack_start(icon, False, False, 0)
            
            lbl_empty = Gtk.Label()
            lbl_empty.set_markup("<b>No hay subsitios creados en este proyecto todavía</b>\nUsa el formulario superior para crear el primero (ej. <i>mikes, corona, etc.</i>).")
            lbl_empty.set_justify(Gtk.Justification.CENTER)
            empty_box.pack_start(lbl_empty, False, False, 0)
            
            self.subsites_list_box.pack_start(empty_box, True, True, 0)
        else:
            for s in subsites:
                card = self.create_subsite_item(s, self.base_dir)
                self.subsites_list_box.pack_start(card, False, False, 0)
                
        self.subsites_list_box.show_all()

    def create_subsite_item(self, subsite, base_dir):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        card.get_style_context().add_class("project-card")
        
        pixbuf = load_icon("drupal.svg", 36)
        if pixbuf:
            img = Gtk.Image.new_from_pixbuf(pixbuf)
            card.pack_start(img, False, False, 0)
            
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        info_box.set_hexpand(True)
        
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_name = Gtk.Label()
        lbl_name.set_markup(f"<b>{subsite['name']}</b>")
        title_row.pack_start(lbl_name, False, False, 0)
        
        lbl_badge = Gtk.Label(label="MULTISITE")
        lbl_badge.get_style_context().add_class("badge")
        lbl_badge.get_style_context().add_class("badge-multisite")
        title_row.pack_start(lbl_badge, False, False, 0)
        
        lbl_db = Gtk.Label(label=f"DB: {subsite['db']}")
        lbl_db.get_style_context().add_class("badge")
        lbl_db.get_style_context().add_class("badge-running")
        title_row.pack_start(lbl_db, False, False, 0)
        
        if subsite.get("config_exists"):
            lbl_cfg = Gtk.Label(label=f"config/{subsite['name']}")
            lbl_cfg.get_style_context().add_class("badge")
            lbl_cfg.get_style_context().add_class("badge-tech")
            title_row.pack_start(lbl_cfg, False, False, 0)
            
        info_box.pack_start(title_row, False, False, 0)
        
        subsite_url = subsite["url"]
        lbl_url = Gtk.Label()
        lbl_url.set_markup(f"🌐 <a href='{subsite_url}'><b>{subsite_url}</b></a>")
        lbl_url.set_halign(Gtk.Align.START)
        info_box.pack_start(lbl_url, False, False, 0)
        
        lbl_path = Gtk.Label()
        lbl_path.set_markup(f"<small><span color='#94a3b8'>📁 {subsite['path']}</span></small>")
        lbl_path.set_halign(Gtk.Align.START)
        info_box.pack_start(lbl_path, False, False, 0)
        
        card.pack_start(info_box, True, True, 0)
        
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions_box.set_valign(Gtk.Align.CENTER)
        
        btn_web = Gtk.Button()
        btn_web.add(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.BUTTON))
        btn_web.set_tooltip_text(f"Abrir {subsite_url} en el navegador")
        btn_web.connect("clicked", lambda b, u=subsite_url: webbrowser.open(u))
        actions_box.pack_start(btn_web, False, False, 0)
        
        btn_quick_cr = Gtk.Button()
        b_cr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_cr_box.pack_start(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_cr_box.pack_start(Gtk.Label(label="Caché"), False, False, 0)
        btn_quick_cr.add(b_cr_box)
        btn_quick_cr.get_style_context().add_class("btn-quick")
        btn_quick_cr.get_style_context().add_class("btn-quick-cache")
        btn_quick_cr.set_tooltip_text(f"Reconstruir caché de {subsite['name']} (drush cr)")
        btn_quick_cr.connect("clicked", lambda b, sn=subsite["name"], su=subsite_url: self.execute_subsite_drush_action("cr", sn, su, base_dir))
        actions_box.pack_start(btn_quick_cr, False, False, 0)
        
        btn_quick_uli = Gtk.Button()
        b_uli_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_uli_box.pack_start(Gtk.Image.new_from_icon_name("dialog-password-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_uli_box.pack_start(Gtk.Label(label="Login"), False, False, 0)
        btn_quick_uli.add(b_uli_box)
        btn_quick_uli.get_style_context().add_class("btn-quick")
        btn_quick_uli.get_style_context().add_class("btn-quick-login")
        btn_quick_uli.set_tooltip_text(f"Iniciar sesión como Admin en {subsite['name']} (drush uli)")
        btn_quick_uli.connect("clicked", lambda b, sn=subsite["name"], su=subsite_url: self.execute_subsite_drush_action("uli", sn, su, base_dir))
        actions_box.pack_start(btn_quick_uli, False, False, 0)
        
        btn_sub_details = Gtk.Button()
        b_sdt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_sdt.pack_start(Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_sdt.pack_start(Gtk.Label(label="Detalles"), False, False, 0)
        btn_sub_details.add(b_sdt)
        btn_sub_details.get_style_context().add_class("btn-quick")
        btn_sub_details.set_tooltip_text(f"Ver información detallada y base de datos de {subsite['name']}")
        btn_sub_details.connect("clicked", lambda b, s=subsite: self.show_subsite_details_dialog(s))
        actions_box.pack_start(btn_sub_details, False, False, 0)
        
        menu_btn_drush = Gtk.MenuButton()
        menu_btn_drush.set_tooltip_text(f"Herramientas Drush para {subsite['name']}")
        menu_btn_drush.get_style_context().add_class("btn-drupal")
        b_drush_lbl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_drush_lbl.pack_start(Gtk.Label(label="Drush"), False, False, 0)
        b_drush_lbl.pack_start(Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.MENU), False, False, 0)
        menu_btn_drush.add(b_drush_lbl)
        
        drush_menu = Gtk.Menu()
        drush_menu.append(create_icon_menu_item("dialog-password-symbolic", "Iniciar Sesión Admin (drush uli)", lambda w: self.execute_subsite_drush_action("uli", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(create_icon_menu_item("view-refresh-symbolic", "Limpiar / Reconstruir Caché (drush cr)", lambda w: self.execute_subsite_drush_action("cr", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(create_icon_menu_item("software-update-available-symbolic", "Actualizar Base de Datos (drush updb)", lambda w: self.execute_subsite_drush_action("updb", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(Gtk.SeparatorMenuItem())
        drush_menu.append(create_icon_menu_item("go-down-symbolic", "Importar Base de Datos (.sql / .sql.gz)", lambda w: self.execute_subsite_drush_action("import_db", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(create_icon_menu_item("go-up-symbolic", "Exportar Base de Datos (.sql.gz)", lambda w: self.execute_subsite_drush_action("export_db", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(Gtk.SeparatorMenuItem())
        drush_menu.append(create_icon_menu_item("document-save-symbolic", "Exportar Configuración (drush cex)", lambda w: self.execute_subsite_drush_action("cex", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(create_icon_menu_item("document-open-symbolic", "Importar Configuración (drush cim)", lambda w: self.execute_subsite_drush_action("cim", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(Gtk.SeparatorMenuItem())
        drush_menu.append(create_icon_menu_item("alarm-symbolic", "Ejecutar Cron (drush cron)", lambda w: self.execute_subsite_drush_action("cron", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(create_icon_menu_item("dialog-information-symbolic", "Estado del Subsitio (drush status)", lambda w: self.execute_subsite_drush_action("status", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(create_icon_menu_item("text-x-generic-symbolic", "Ver Logs Recientes (drush watchdog)", lambda w: self.execute_subsite_drush_action("watchdog", subsite["name"], subsite_url, base_dir)))
        drush_menu.append(Gtk.SeparatorMenuItem())
        drush_menu.append(create_icon_menu_item("utilities-terminal-symbolic", "Abrir SSH en este Subsitio", lambda w: self.execute_subsite_drush_action("ssh", subsite["name"], subsite_url, base_dir)))
        
        drush_menu.show_all()
        menu_btn_drush.set_popup(drush_menu)
        actions_box.pack_start(menu_btn_drush, False, False, 0)
        
        btn_folder = Gtk.Button()
        btn_folder.add(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON))
        btn_folder.set_tooltip_text("Abrir carpeta de este subsitio")
        btn_folder.connect("clicked", lambda b, p=subsite["path"]: subprocess.Popen(["xdg-open", p]))
        actions_box.pack_start(btn_folder, False, False, 0)
        
        btn_del = Gtk.Button()
        btn_del.add(Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON))
        btn_del.set_tooltip_text("Eliminar este subsitio del multisite")
        btn_del.connect("clicked", lambda b, s=subsite: self.confirm_delete_subsite(s, base_dir))
        actions_box.pack_start(btn_del, False, False, 0)
        
        card.pack_start(actions_box, False, False, 0)
        return card

    def execute_base_ddev_action(self, action):
        dialog = ProgressDialog(self.main_app, title=f"DDEV: {action.capitalize()} {self.base_name}")
        dialog.set_status(f"Ejecutando ddev {action} en {self.base_name}...")
        
        def task():
            cmd = ["ddev", action, "-y"] if action == "start" else ["ddev", action]
            proc = subprocess.Popen(cmd, cwd=self.base_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(proc.stdout.readline, ''):
                GLib.idle_add(dialog.append_log, line)
            proc.stdout.close()
            proc.wait()
            success = (proc.returncode == 0)
            url = f"https://{self.base_name}.ddev.site" if action == "start" else ""
            msg = f"Proyecto base {self.base_name} {action} completado" if success else f"Error al ejecutar {action}"
            GLib.idle_add(dialog.finish, success, msg, url, self.base_dir)
            GLib.idle_add(self.refresh_subsites)
            GLib.idle_add(self.main_app.refresh_projects)
            
        threading.Thread(target=task, daemon=True).start()

    def execute_base_composer_install(self):
        dialog = ProgressDialog(self.main_app, title=f"Composer Install: {self.base_name}")
        dialog.set_status(f"Ejecutando ddev composer install en {self.base_name}...")
        
        def task():
            cmd = ["ddev", "composer", "install"]
            self.run_subproc(cmd, self.base_dir, dialog)
            GLib.idle_add(dialog.finish, True, "Composer install completado", "", self.base_dir)
            GLib.idle_add(self.refresh_subsites)
            
        threading.Thread(target=task, daemon=True).start()

    def execute_subsite_drush_action(self, action_key, subsite_name, subsite_url, base_dir):
        if action_key == "ssh":
            self.main_app.open_terminal(base_dir, f"ddev drush --uri={subsite_url} status; ddev ssh")
            return

        st = (self.proj.get("status", "") if self.proj else "").lower()
        is_running = "running" in st or "ok" in st

        if not is_running:
            confirm = Gtk.MessageDialog(
                transient_for=self.main_app,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=f"El proyecto base '{self.base_name}' está detenido."
            )
            confirm.format_secondary_text(
                f"Para realizar esta operación en el subsitio '{subsite_name}', es necesario iniciar el entorno DDEV.\n\n¿Deseas iniciar el proyecto ahora y continuar con la acción?"
            )
            res = confirm.run()
            confirm.destroy()
            if res != Gtk.ResponseType.OK:
                return

        if action_key == "import_db":
            dialog = Gtk.FileChooserDialog(
                title=f"Seleccionar archivo SQL para importar en {subsite_name}",
                parent=self.main_app,
                action=Gtk.FileChooserAction.OPEN
            )
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
            
            filter_sql = Gtk.FileFilter()
            filter_sql.set_name("Archivos SQL (*.sql, *.sql.gz, *.tar.gz, *.zip)")
            filter_sql.add_pattern("*.sql")
            filter_sql.add_pattern("*.sql.gz")
            filter_sql.add_pattern("*.tar.gz")
            filter_sql.add_pattern("*.zip")
            filter_sql.add_pattern("*.gz")
            dialog.add_filter(filter_sql)
            
            filter_all = Gtk.FileFilter()
            filter_all.set_name("Todos los archivos")
            filter_all.add_pattern("*")
            dialog.add_filter(filter_all)
            dialog.set_modal(True)
            dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
            dialog.present()
            
            resp = dialog.run()
            src_file = dialog.get_filename()
            dialog.destroy()
            
            if resp == Gtk.ResponseType.OK and src_file:
                confirm = Gtk.MessageDialog(
                    transient_for=self.main_app,
                    flags=0,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK_CANCEL,
                    text=f"¿Confirmas la importación en '{subsite_name}'?"
                )
                confirm.format_secondary_text(f"Se importará el archivo:\n{os.path.basename(src_file)}\n\n⚠️ ADVERTENCIA: Esta acción sobreescribirá las tablas existentes en la base de datos '{subsite_name}'.")
                c_resp = confirm.run()
                confirm.destroy()
                
                if c_resp == Gtk.ResponseType.OK:
                    prog_dialog = ProgressDialog(self.main_app, title=f"Importando BD: {subsite_name}")
                    prog_dialog.set_status(f"Importando {os.path.basename(src_file)} en base de datos '{subsite_name}'...")
                    
                    def task():
                        try:
                            def log(t):
                                GLib.idle_add(prog_dialog.append_log, t)
                            log(f"📥 Ejecutando 'ddev import-db --database={subsite_name} --file={src_file}'...\n")
                            proc = subprocess.Popen(["ddev", "import-db", f"--database={subsite_name}", f"--file={src_file}"], cwd=base_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                            for line in iter(proc.stdout.readline, ''):
                                log(line)
                            proc.stdout.close()
                            proc.wait()
                            
                            if proc.returncode == 0:
                                log(f"\n⚡ Reconstruyendo caché de {subsite_name} (drush cr)...\n")
                                subprocess.run(["ddev", "drush", f"--uri={subsite_url}", "cr"], cwd=base_dir, capture_output=True)
                                GLib.idle_add(prog_dialog.finish, True, f"Base de datos '{subsite_name}' importada con éxito", subsite_url, base_dir)
                            else:
                                GLib.idle_add(prog_dialog.finish, False, f"Error al importar base de datos en '{subsite_name}'", "", base_dir)
                        except Exception as ex:
                            GLib.idle_add(prog_dialog.finish, False, f"Error: {ex}", "", base_dir)
                            
                    threading.Thread(target=task, daemon=True).start()
            return

        if action_key == "export_db":
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"{subsite_name}_db_{now_str}.sql.gz"
            
            dialog = Gtk.FileChooserDialog(
                title=f"Guardar respaldo de base de datos de {subsite_name}",
                parent=self.main_app,
                action=Gtk.FileChooserAction.SAVE
            )
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            dialog.set_current_name(default_filename)
            dialog.set_do_overwrite_confirmation(True)
            dialog.set_modal(True)
            dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
            dialog.present()
            
            downloads_dir = os.path.expanduser("~/Descargas")
            if not os.path.exists(downloads_dir):
                downloads_dir = os.path.expanduser("~/Downloads")
            if os.path.exists(downloads_dir):
                dialog.set_current_folder(downloads_dir)
            else:
                dialog.set_current_folder(base_dir)
                
            resp = dialog.run()
            out_file = dialog.get_filename()
            dialog.destroy()
            
            if resp == Gtk.ResponseType.OK and out_file:
                prog_dialog = ProgressDialog(self.main_app, title=f"Exportando BD: {subsite_name}")
                prog_dialog.set_status(f"Exportando base de datos '{subsite_name}'...")
                
                def task():
                    try:
                        def log(t):
                            GLib.idle_add(prog_dialog.append_log, t)
                        log(f"📦 Ejecutando 'ddev export-db --database={subsite_name} --file={out_file}'...\n")
                        proc = subprocess.Popen(["ddev", "export-db", f"--database={subsite_name}", f"--file={out_file}"], cwd=base_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                        for line in iter(proc.stdout.readline, ''):
                            log(line)
                        proc.stdout.close()
                        proc.wait()
                        
                        success = (proc.returncode == 0)
                        msg = f"Base de datos '{subsite_name}' exportada con éxito en:\n{out_file}" if success else f"Error al exportar la base de datos '{subsite_name}'"
                        GLib.idle_add(prog_dialog.finish, success, msg, "", os.path.dirname(out_file))
                    except Exception as ex:
                        GLib.idle_add(prog_dialog.finish, False, f"Error: {ex}", "", base_dir)
                        
                threading.Thread(target=task, daemon=True).start()
            return
            
        drush_map = {
            "cr": ("Limpiar Caché", ["cr"], "Caché reconstruida con éxito"),
            "uli": ("Login Admin", ["uli"], "Enlace de inicio de sesión generado"),
            "updb": ("Actualizar BD", ["updatedb", "-y"], "Actualizaciones de base de datos completadas"),
            "cex": ("Exportar Configuración", ["config:export", "-y"], "Configuración exportada"),
            "cim": ("Importar Configuración", ["config:import", "-y"], "Configuración importada"),
            "cron": ("Ejecutar Cron", ["cron"], "Cron ejecutado con éxito"),
            "status": ("Estado del Sitio", ["status"], "Estado obtenido"),
            "watchdog": ("Ver Logs", ["watchdog:show", "--count=30"], "Logs obtenidos")
        }
        
        info = drush_map.get(action_key)
        if not info:
            return
            
        title, args, success_msg = info
        cmd = ["ddev", "drush", f"--uri={subsite_url}"] + args
        cmd_str = " ".join(cmd)
        
        dialog = ProgressDialog(self.main_app, title=f"Drush: {title} ({subsite_name})")
        dialog.set_status(f"Ejecutando en {subsite_name}...")
        
        def task():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t)
                log(f"$ {cmd_str}\n\n")
                proc = subprocess.Popen(cmd, cwd=base_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                output_lines = []
                for line in iter(proc.stdout.readline, ''):
                    output_lines.append(line)
                    log(line)
                proc.stdout.close()
                proc.wait()
                
                success = (proc.returncode == 0)
                full_output = "".join(output_lines)
                detected_url = ""
                
                if action_key == "uli" and success:
                    clean_output = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', full_output)
                    match = re.search(r'(https?://[^\s]+(?:/user/reset/[^\s]+|/login[^\s]*))', clean_output)
                    if not match:
                        match = re.search(r'(https?://[^\s]+)', clean_output)
                    if match:
                        raw_url = match.group(1).strip().rstrip('.,;)')
                        fixed_url = re.sub(r'^https?://(default|127\.0\.0\.1|localhost)(:\d+)?', subsite_url.rstrip('/'), raw_url)
                        detected_url = fixed_url
                        try:
                            webbrowser.open(detected_url)
                        except Exception:
                            pass
                            
                finish_msg = success_msg if success else f"Error ejecutando {title}"
                GLib.idle_add(dialog.finish, success, finish_msg, detected_url or subsite_url, base_dir)
            except Exception as ex:
                GLib.idle_add(dialog.append_log, f"\nExcepción: {ex}\n")
                GLib.idle_add(dialog.finish, False, f"Error: {ex}", "", base_dir)
                
        threading.Thread(target=task, daemon=True).start()

    def on_create_subsite_clicked(self, widget):
        raw_name = self.entry_subsite_name.get_text().strip()
        slug = re.sub(r'[^a-zA-Z0-9_-]', '-', raw_name).lower()
        if not slug:
            msg = Gtk.MessageDialog(transient_for=self.main_app, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text="Por favor ingresa un nombre para el subsitio (ej. mikes, corona)")
            msg.run()
            msg.destroy()
            self.entry_subsite_name.grab_focus()
            return

        base_dir = self.base_dir
        if not os.path.exists(base_dir):
            msg = Gtk.MessageDialog(transient_for=self.main_app, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=f"El proyecto base '{base_dir}' no existe")
            msg.run()
            msg.destroy()
            return

        profile = self.combo_subsite_profile.get_active_id() or "minimal"
        auto_install = self.chk_subsite_auto_install.get_active()
        subsite_domain = f"{slug}.ddev.site"
        subsite_url = f"https://{subsite_domain}"

        dialog = ProgressDialog(self.main_app, title=f"Aprovisionando Subsitio: {slug}")
        dialog.set_status(f"Creando subsitio {slug} ({subsite_url})...")

        def task():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t + "\n")
                def set_st(s):
                    GLib.idle_add(dialog.set_status, s)

                log(f"🚀 Iniciando aprovisionamiento de subsitio: {slug}")
                log(f"🌐 URL: {subsite_url}")
                log(f"📁 Directorio base: {base_dir}")
                log("="*50)

                # 1. Ensure DDEV config exists
                ddev_cfg = os.path.join(base_dir, ".ddev", "config.yaml")
                if not os.path.exists(ddev_cfg):
                    set_st("Configurando DDEV en proyecto base...")
                    base_name = os.path.basename(base_dir)
                    cfg_cmd = ["ddev", "config", f"--project-name={base_name}", "--project-type=drupal10", "--docroot=docroot", "--php-version=8.3", "--database=mariadb:10.11"]
                    self.run_subproc(cfg_cmd, base_dir, dialog)

                # 2. Add subsite domain to additional_fqdns via native ddev config
                set_st(f"Registrando dominio {subsite_domain} en DDEV...")
                self.update_ddev_fqdns(base_dir, add_subsite=slug)
                log(f"✓ Dominio {subsite_domain} registrado en DDEV.")

                # 3. Ensure DDEV is started
                set_st("Iniciando entorno DDEV...")
                self.run_subproc(["ddev", "start", "-y"], base_dir, dialog)

                # 4. Create database in MariaDB/MySQL
                set_st(f"Creando base de datos '{slug}' en MariaDB...")
                db_sql = f"CREATE DATABASE IF NOT EXISTS `{slug}`; GRANT ALL PRIVILEGES ON `{slug}`.* TO 'db'@'%'; GRANT ALL PRIVILEGES ON *.* TO 'db'@'%'; FLUSH PRIVILEGES;"
                self.run_subproc(["ddev", "mysql", "-uroot", "-proot", "-hdb", "-e", db_sql], base_dir, dialog)
                log(f"✓ Base de datos '{slug}' creada en MariaDB con permisos totales.")

                # 5. Create folder structure docroot/sites/<slug>/files
                docroot_dir = "docroot" if os.path.exists(os.path.join(base_dir, "docroot")) else ("web" if os.path.exists(os.path.join(base_dir, "web")) else ".")
                target_site_dir = os.path.join(base_dir, docroot_dir, "sites", slug)
                target_files_dir = os.path.join(target_site_dir, "files")
                os.makedirs(target_files_dir, exist_ok=True)
                os.chmod(target_files_dir, 0o777)

                # 6. Create settings.php
                settings_file = os.path.join(target_site_dir, "settings.php")
                settings_code = f"""<?php
/**
 * Settings for Drupal subsite: {slug}
 * Generated automatically by DDEV Studio.
 */

$databases['default']['default'] = [
  'database' => '{slug}',
  'username' => 'db',
  'password' => 'db',
  'host' => 'db',
  'port' => '3306',
  'driver' => 'mysql',
  'prefix' => '',
];

$settings['config_sync_directory'] = '../config/{slug}';
$settings['file_public_path'] = 'sites/{slug}/files';
$settings['hash_salt'] = hash('sha256', '{slug}_ddev_salt');

// Include default settings
if (file_exists(DRUPAL_ROOT . '/sites/default/default.settings.php')) {{
  require DRUPAL_ROOT . '/sites/default/default.settings.php';
}}

// Config split activation if available
if (file_exists(DRUPAL_ROOT . '/../config/{slug}')) {{
  $config['config_split.config_split.{slug}']['status'] = TRUE;
}}

// Local settings overrides
if (file_exists(__DIR__ . '/local.settings.php')) {{
  include __DIR__ . '/local.settings.php';
}}
"""
                with open(settings_file, "w") as f:
                    f.write(settings_code)
                log(f"✓ Archivo settings.php creado en {docroot_dir}/sites/{slug}/.")

                # 7. Create Drush site alias
                drush_sites_dir = os.path.join(base_dir, "drush", "sites")
                os.makedirs(drush_sites_dir, exist_ok=True)
                alias_file = os.path.join(drush_sites_dir, f"{slug}.site.yml")
                alias_code = f"""{slug}:
  root: /var/www/html/{docroot_dir}
  uri: {subsite_url}
"""
                with open(alias_file, "w") as f:
                    f.write(alias_code)
                log(f"✓ Alias de Drush creado en drush/sites/{slug}.site.yml.")

                # 8. Ensure dynamic sites mapping in <docroot>/sites/sites.php
                sites_php_file = os.path.join(base_dir, docroot_dir, "sites", "sites.php")
                if not os.path.exists(sites_php_file):
                    with open(sites_php_file, "w") as f:
                        f.write("""<?php
/**
 * @file
 * Drupal multi-site configuration file for DDEV.
 */

// Dynamic DDEV multisite mapping
$sites_base = __DIR__;
if (is_dir($sites_base)) {
  $entries = scandir($sites_base);
  foreach ($entries as $entry) {
    if ($entry !== '.' && $entry !== '..' && $entry !== 'default' && $entry !== 'all' && $entry !== 'g' && $entry !== 'settings' && is_dir($sites_base . '/' . $entry)) {
      $sites[$entry . '.ddev.site'] = $entry;
      if (!empty($_ENV['DDEV_PROJECT'])) {
        $sites[$entry . '.' . $_ENV['DDEV_PROJECT'] . '.ddev.site'] = $entry;
      }
      $sites['local.' . $entry . '.com'] = $entry;
    }
  }
}
""")
                    log(f"✓ Archivo {docroot_dir}/sites/sites.php creado con mapeo dinámico.")
                else:
                    try:
                        with open(sites_php_file, "r") as f:
                            s_content = f.read()
                        if f"{subsite_domain}" not in s_content and "$sites_base" not in s_content and "ddev.site" not in s_content:
                            with open(sites_php_file, "a") as f:
                                f.write(f"\n$sites['{subsite_domain}'] = '{slug}';\n")
                            log(f"✓ Mapeo {subsite_domain} agregado a {docroot_dir}/sites/sites.php.")
                    except Exception as ex:
                        log(f"Nota en sites.php: {ex}")

                # Also support Acquia factory-hooks if directory exists
                hook_dir = os.path.join(base_dir, "factory-hooks", "pre-sites-php")
                if os.path.exists(hook_dir):
                    hook_file = os.path.join(hook_dir, "sites.local.php")
                    if not os.path.exists(hook_file):
                        with open(hook_file, "w") as f:
                            f.write("""<?php
if (!file_exists('/var/acquia')) {
  $sites_base = defined('DRUPAL_ROOT') ? DRUPAL_ROOT . '/sites' : __DIR__ . '/../../docroot/sites';
  if (is_dir($sites_base)) {
    $entries = scandir($sites_base);
    foreach ($entries as $entry) {
      if ($entry !== '.' && $entry !== '..' && $entry !== 'default' && $entry !== 'g' && $entry !== 'settings' && $entry !== 'all' && is_dir($sites_base . '/' . $entry)) {
        $sites[$entry . '.ddev.site'] = $entry;
        $sites[$entry . '.co-aguila.ddev.site'] = $entry;
        $sites['local.' . $entry . '.com'] = $entry;
      }
    }
  }
}
""")

                # 9. Restart DDEV to bind the new domain to router
                set_st("Reiniciando router de DDEV para activar el dominio...")
                self.run_subproc(["ddev", "restart", "-y"], base_dir, dialog)

                # 10. Auto-install if selected
                if auto_install and profile != "none":
                    vendor_drush = os.path.join(base_dir, "vendor", "bin", "drush")
                    if not os.path.exists(vendor_drush):
                        set_st("Instalando dependencias de Composer (Drupal Core y Drush)...")
                        log("📦 'drush' no detectado en vendor. Ejecutando 'ddev composer install'...")
                        self.run_subproc(["ddev", "composer", "install"], base_dir, dialog)
                        log("✓ Dependencias de Composer instaladas.")

                    set_st(f"Instalando perfil '{profile}' en {slug} con Drush...")
                    inst_cmd = [
                        "ddev", "drush", f"--uri={subsite_url}",
                        "site:install", profile,
                        f"--db-url=mysql://root:root@db:3306/{slug}",
                        f"--site-name={slug.capitalize()}",
                        "--account-name=admin",
                        "--account-pass=admin",
                        "-y"
                    ]
                    self.run_subproc(inst_cmd, base_dir, dialog)
                    log(f"\n🎉 Subsitio '{slug}' instalado con perfil '{profile}'!")
                    log("Credenciales: admin / admin")

                # 11. Generate ULI
                detected_login_url = ""
                try:
                    res = subprocess.run(["ddev", "drush", f"--uri={subsite_url}", "uli"], cwd=base_dir, capture_output=True, text=True)
                    if res.returncode == 0 and res.stdout:
                        clean_out = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', res.stdout)
                        m = re.search(r'(https?://[^\s]+)', clean_out)
                        if m:
                            raw_u = m.group(1).strip().rstrip('.,;)')
                            fixed_u = re.sub(r'^https?://(default|127\.0\.0\.1|localhost)(:\d+)?', subsite_url, raw_u)
                            detected_login_url = fixed_u
                            log(f"🔑 Enlace de login administrador: {detected_login_url}")
                            try:
                                webbrowser.open(detected_login_url)
                            except Exception:
                                pass
                except Exception:
                    pass

                log("\n" + "="*50)
                log(f"¡Subsitio '{slug}' aprovisionado y listo!")
                log(f"URL: {subsite_url}")
                GLib.idle_add(dialog.finish, True, f"¡Subsitio '{slug}' listo!", detected_login_url or subsite_url, target_site_dir)
                GLib.idle_add(self.refresh_subsites)
                GLib.idle_add(self.main_app.refresh_projects)

            except Exception as ex:
                log(f"\n❌ ERROR: {str(ex)}")
                GLib.idle_add(dialog.finish, False, f"Error creando subsitio: {str(ex)}", "", base_dir)

        threading.Thread(target=task, daemon=True).start()

    def confirm_delete_subsite(self, subsite, base_dir):
        s_name = subsite["name"]
        s_path = subsite["path"]
        
        dialog = Gtk.MessageDialog(
            transient_for=self.main_app,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"¿Estás seguro de eliminar el subsitio '{s_name}'?"
        )
        dialog.format_secondary_text(
            f"Se eliminará la base de datos MariaDB '{s_name}', el dominio y la carpeta:\n{s_path}\n\nNota: La carpeta del proyecto base permanecerá intacta."
        )
        res = dialog.run()
        dialog.destroy()
        
        if res == Gtk.ResponseType.OK:
            del_dialog = ProgressDialog(self.main_app, title=f"Eliminando Subsitio {s_name}")
            del_dialog.set_status(f"Eliminando base de datos y archivos de {s_name}...")
            
            def task():
                try:
                    # 1. Drop DB
                    GLib.idle_add(del_dialog.append_log, f"Eliminando base de datos '{s_name}'...\n")
                    subprocess.run(["ddev", "mysql", "-uroot", "-proot", "-hdb", "-e", f"DROP DATABASE IF EXISTS `{s_name}`;"], cwd=base_dir, capture_output=True)
                    
                    # 2. Fix Drupal read-only permissions (555/444) and remove folder
                    if os.path.exists(s_path):
                        GLib.idle_add(del_dialog.append_log, f"Eliminando carpeta {s_path}...\n")
                        subprocess.run(["chmod", "-R", "u+w", s_path], capture_output=True)
                        shutil.rmtree(s_path, ignore_errors=True)
                        if os.path.exists(s_path):
                            subprocess.run(["rm", "-rf", s_path], capture_output=True)
                        
                    # 3. Remove Drush alias
                    alias_file = os.path.join(base_dir, "drush", "sites", f"{s_name}.site.yml")
                    if os.path.exists(alias_file):
                        try:
                            os.remove(alias_file)
                        except Exception:
                            pass
                            
                    # 4. Remove domain from additional_fqdns via native ddev config
                    self.update_ddev_fqdns(base_dir, remove_subsite=s_name)
                            
                    # 5. Restart DDEV to release domain
                    GLib.idle_add(del_dialog.append_log, f"Actualizando router de DDEV...\n")
                    subprocess.run(["ddev", "restart", "-y"], cwd=base_dir, capture_output=True)
                        
                    GLib.idle_add(del_dialog.finish, True, f"Subsitio '{s_name}' eliminado con éxito", "", base_dir)
                    GLib.idle_add(self.refresh_subsites)
                    GLib.idle_add(self.main_app.refresh_projects)
                except Exception as ex:
                    GLib.idle_add(del_dialog.finish, False, f"Error: {ex}", "", base_dir)
                    
            threading.Thread(target=task, daemon=True).start()
