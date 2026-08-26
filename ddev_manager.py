#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DDEV Studio - Gestor Visual de Proyectos DDEV para Ubuntu MATE
"""

import os
import sys
import json
import re
import subprocess
import threading
import shutil
import webbrowser
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(APP_DIR, "icons")
DEFAULT_SITES_DIR = os.path.expanduser("~/sites")

CUSTOM_CSS = b"""
.header-title {
    font-size: 16px;
    font-weight: bold;
}
.header-subtitle {
    font-size: 11px;
    opacity: 0.8;
}
.framework-card {
    border-radius: 12px;
    border: 2px solid rgba(128, 128, 128, 0.25);
    background: alpha(@theme_base_color, 0.6);
    padding: 14px;
    transition: all 200ms ease-in-out;
}
.framework-card:hover {
    border-color: @theme_selected_bg_color;
    background: alpha(@theme_selected_bg_color, 0.1);
}
.framework-card.selected {
    border-color: @theme_selected_bg_color;
    background: alpha(@theme_selected_bg_color, 0.18);
}
.badge {
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}
.badge-running {
    background-color: #10b981;
    color: white;
}
.badge-stopped {
    background-color: #6b7280;
    color: white;
}
.badge-paused {
    background-color: #f59e0b;
    color: white;
}
.badge-tech {
    background-color: alpha(@theme_selected_bg_color, 0.25);
    color: @theme_text_color;
}
.option-highlight-box {
    border-radius: 10px;
    border: 1px solid alpha(@theme_selected_bg_color, 0.4);
    background: alpha(@theme_selected_bg_color, 0.08);
    padding: 12px 16px;
}
.btn-primary {
    background-color: #0284c7;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 8px 18px;
}
.btn-primary:hover {
    background-color: #0369a1;
}
.console-view {
    font-family: 'Monospace', monospace;
    font-size: 11px;
    background-color: #1e1e1e;
    color: #e0e0e0;
    border-radius: 8px;
}
.project-card {
    border-radius: 10px;
    border: 1px solid rgba(128, 128, 128, 0.2);
    padding: 12px;
    margin-bottom: 8px;
    background: alpha(@theme_base_color, 0.4);
}
.project-card:hover {
    border-color: rgba(128, 128, 128, 0.4);
    background: alpha(@theme_base_color, 0.8);
}
"""

FRAMEWORKS = [
    {
        "id": "drupal",
        "name": "Drupal",
        "category": "CMS Empresarial",
        "desc": "CMS potente y modular con Drush. Soporta versiones 11, 10, 9, 8 y 7.",
        "icon": "drupal.svg",
        "php": "8.3",
        "docroot": "web",
        "db": "mariadb:10.11",
    },
    {
        "id": "wordpress",
        "name": "WordPress",
        "category": "CMS",
        "desc": "El CMS más popular del mundo. Con WP-CLI y base de datos lista.",
        "icon": "wordpress.svg",
        "php": "8.2",
        "docroot": ".",
        "db": "mariadb:10.11",
    },
    {
        "id": "laravel",
        "name": "Laravel",
        "category": "PHP Framework",
        "desc": "Framework PHP elegante con Artisan, migraciones y docroot public.",
        "icon": "laravel.svg",
        "php": "8.3",
        "docroot": "public",
        "db": "mysql:8.0",
    },
    {
        "id": "react",
        "name": "React (Vite)",
        "category": "Frontend SPA",
        "desc": "Desarrollo rápido con Vite + React (TypeScript/JavaScript).",
        "icon": "react.svg",
        "php": "8.2",
        "docroot": "dist",
        "db": "mariadb:10.11",
    },
    {
        "id": "vue",
        "name": "Vue 3 (Vite)",
        "category": "Frontend SPA",
        "desc": "Vite + Vue 3 con Fast Refresh y Node.js integrado.",
        "icon": "vue.svg",
        "php": "8.2",
        "docroot": "dist",
        "db": "mariadb:10.11",
    },
    {
        "id": "php",
        "name": "PHP Plano / HTML",
        "category": "Básico",
        "desc": "Entorno limpio para scripts PHP o páginas web simples.",
        "icon": "php.svg",
        "php": "8.3",
        "docroot": ".",
        "db": "mariadb:10.11",
    },
    {
        "id": "symfony",
        "name": "Symfony",
        "category": "PHP Framework",
        "desc": "Framework robusto para aplicaciones PHP de alto rendimiento.",
        "icon": "symfony.svg",
        "php": "8.3",
        "docroot": "public",
        "db": "mariadb:10.11",
    }
]

DRUPAL_VERSIONS = [
    {"id": "11", "label": "Drupal 11 (Última versión recomendada - PHP 8.3/8.4)", "php": "8.3", "docroot": "web", "type": "drupal11"},
    {"id": "10", "label": "Drupal 10 (LTS Estable - PHP 8.3/8.2)", "php": "8.3", "docroot": "web", "type": "drupal10"},
    {"id": "9", "label": "Drupal 9 (PHP 8.1)", "php": "8.1", "docroot": "web", "type": "drupal9"},
    {"id": "8", "label": "Drupal 8 (PHP 7.4)", "php": "7.4", "docroot": "web", "type": "drupal8"},
    {"id": "7", "label": "Drupal 7 (Legacy - PHP 7.4)", "php": "7.4", "docroot": ".", "type": "drupal7"},
]


def load_icon(name, size=48):
    path = os.path.join(ICONS_DIR, name)
    if os.path.exists(path):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        except Exception:
            pass
    return None


class ProgressDialog(Gtk.Dialog):
    def __init__(self, parent, title="Ejecutando tarea"):
        super().__init__(title=title, transient_for=parent, flags=Gtk.DialogFlags.MODAL)
        self.set_default_size(680, 480)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.spinner = Gtk.Spinner()
        self.spinner.start()
        header_box.pack_start(self.spinner, False, False, 0)
        
        self.status_label = Gtk.Label(label="Preparando...")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_markup("<b>Iniciando operación...</b>")
        header_box.pack_start(self.status_label, True, True, 0)
        box.pack_start(header_box, False, False, 0)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_pulse_step(0.1)
        box.pack_start(self.progress_bar, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.get_style_context().add_class("console-view")
        self.text_buffer = self.text_view.get_buffer()
        scrolled.add(self.text_view)
        box.pack_start(scrolled, True, True, 0)
        
        self.action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.action_box.set_halign(Gtk.Align.END)
        box.pack_start(self.action_box, False, False, 0)
        
        self.btn_open_browser = Gtk.Button(label="🌐 Abrir en Navegador")
        self.btn_open_browser.connect("clicked", self.on_open_browser)
        self.action_box.pack_start(self.btn_open_browser, False, False, 0)
        
        self.btn_open_folder = Gtk.Button(label="📁 Abrir Carpeta")
        self.btn_open_folder.connect("clicked", self.on_open_folder)
        self.action_box.pack_start(self.btn_open_folder, False, False, 0)
        
        self.btn_close = Gtk.Button(label="Cerrar")
        self.btn_close.connect("clicked", lambda b: self.destroy())
        self.action_box.pack_start(self.btn_close, False, False, 0)
        
        self.action_box.set_no_show_all(True)
        self.action_box.hide()
        
        self.project_url = ""
        self.project_path = ""
        
        self.show_all()
        
    def append_log(self, text):
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, text)
        mark = self.text_buffer.create_mark(None, self.text_buffer.get_end_iter(), False)
        self.text_view.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
        
    def set_status(self, text, pulse=True):
        self.status_label.set_markup(f"<b>{text}</b>")
        if pulse:
            self.progress_bar.pulse()
            
    def finish(self, success, message, url="", path=""):
        self.spinner.stop()
        self.spinner.hide()
        self.progress_bar.set_fraction(1.0 if success else 0.0)
        self.project_url = url
        self.project_path = path
        
        if success:
            self.status_label.set_markup(f"<span color='#10b981'><b>✓ {message}</b></span>")
            if not url:
                self.btn_open_browser.hide()
            else:
                self.btn_open_browser.show()
            if not path:
                self.btn_open_folder.hide()
            else:
                self.btn_open_folder.show()
        else:
            self.status_label.set_markup(f"<span color='#ef4444'><b>✗ {message}</b></span>")
            self.btn_open_browser.hide()
            self.btn_open_folder.hide()
            
        self.action_box.show()
        self.btn_close.grab_focus()
        
    def on_open_browser(self, widget):
        if self.project_url:
            webbrowser.open(self.project_url)
            
    def on_open_folder(self, widget):
        if self.project_path and os.path.exists(self.project_path):
            subprocess.Popen(["xdg-open", self.project_path])


class DDEVManagerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="DDEV Studio")
        self.set_default_size(960, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        ddev_icon = load_icon("ddev.svg", 64)
        if ddev_icon:
            self.set_icon(ddev_icon)
            
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CUSTOM_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        self.build_headerbar()
        self.build_main_layout()
        
        GLib.idle_add(self.refresh_projects)

    def build_headerbar(self):
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "DDEV Studio"
        header.props.subtitle = "Ubuntu MATE"
        self.set_titlebar(header)
        
        btn_refresh = Gtk.Button()
        icon_refresh = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        btn_refresh.add(icon_refresh)
        btn_refresh.set_tooltip_text("Actualizar lista de proyectos")
        btn_refresh.connect("clicked", lambda b: self.refresh_projects())
        header.pack_start(btn_refresh)
        
        btn_poweroff = Gtk.Button()
        icon_poweroff = Gtk.Image.new_from_icon_name("system-shutdown-symbolic", Gtk.IconSize.BUTTON)
        btn_poweroff.add(icon_poweroff)
        btn_poweroff.set_tooltip_text("Detener todos los contenedores DDEV (ddev poweroff)")
        btn_poweroff.connect("clicked", self.on_global_poweroff)
        header.pack_end(btn_poweroff)
        
        btn_info = Gtk.Button()
        icon_info = Gtk.Image.new_from_icon_name("help-about-symbolic", Gtk.IconSize.BUTTON)
        btn_info.add(icon_info)
        btn_info.set_tooltip_text("Acerca de DDEV Studio")
        btn_info.connect("clicked", self.on_show_about)
        header.pack_end(btn_info)

    def build_main_layout(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)
        
        self.notebook = Gtk.Notebook()
        main_box.pack_start(self.notebook, True, True, 0)
        
        tab_new = self.build_tab_new_project()
        lbl_new = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_new.pack_start(Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_new.pack_start(Gtk.Label(label="Nuevo Proyecto"), False, False, 0)
        lbl_new.show_all()
        self.notebook.append_page(tab_new, lbl_new)
        
        tab_projects = self.build_tab_projects()
        lbl_proj = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_proj.pack_start(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.MENU), False, False, 0)
        self.lbl_proj_title = Gtk.Label(label="Mis Proyectos")
        lbl_proj.pack_start(self.lbl_proj_title, False, False, 0)
        lbl_proj.show_all()
        self.notebook.append_page(tab_projects, lbl_proj)
        
        tab_tools = self.build_tab_tools()
        lbl_tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_tools.pack_start(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_tools.pack_start(Gtk.Label(label="Herramientas"), False, False, 0)
        lbl_tools.show_all()
        self.notebook.append_page(tab_tools, lbl_tools)

    def build_tab_new_project(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(20)
        box.set_margin_bottom(24)
        scrolled.add(box)
        
        sec_title = Gtk.Label()
        sec_title.set_markup("<b>1. Información del Proyecto</b>")
        sec_title.set_halign(Gtk.Align.START)
        box.pack_start(sec_title, False, False, 0)
        
        grid_info = Gtk.Grid()
        grid_info.set_column_spacing(16)
        grid_info.set_row_spacing(10)
        box.pack_start(grid_info, False, False, 0)
        
        lbl_name = Gtk.Label(label="Nombre:")
        lbl_name.set_halign(Gtk.Align.END)
        grid_info.attach(lbl_name, 0, 0, 1, 1)
        
        self.entry_name = Gtk.Entry()
        self.entry_name.set_placeholder_text("ej. mi-sitio, blog, tienda, app")
        self.entry_name.set_hexpand(True)
        self.entry_name.connect("changed", self.on_project_name_changed)
        grid_info.attach(self.entry_name, 1, 0, 1, 1)
        
        lbl_dir = Gtk.Label(label="Ubicación:")
        lbl_dir.set_halign(Gtk.Align.END)
        grid_info.attach(lbl_dir, 0, 1, 1, 1)
        
        dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_path = Gtk.Entry()
        self.entry_path.set_text(DEFAULT_SITES_DIR)
        self.entry_path.set_hexpand(True)
        dir_box.pack_start(self.entry_path, True, True, 0)
        
        btn_browse = Gtk.Button(label="Examinar...")
        btn_browse.connect("clicked", self.on_browse_folder)
        dir_box.pack_start(btn_browse, False, False, 0)
        grid_info.attach(dir_box, 1, 1, 1, 1)
        
        self.lbl_path_preview = Gtk.Label()
        self.lbl_path_preview.set_halign(Gtk.Align.START)
        self.lbl_path_preview.set_markup(f"<small>Carpeta final: <tt>{DEFAULT_SITES_DIR}/</tt></small>")
        grid_info.attach(self.lbl_path_preview, 1, 2, 1, 1)
        
        sec_fw = Gtk.Label()
        sec_fw.set_markup("<b>2. Selecciona la Tecnología</b>")
        sec_fw.set_halign(Gtk.Align.START)
        sec_fw.set_margin_top(12)
        box.pack_start(sec_fw, False, False, 0)
        
        self.flowbox_fw = Gtk.FlowBox()
        self.flowbox_fw.set_valign(Gtk.Align.START)
        self.flowbox_fw.set_max_children_per_line(4)
        self.flowbox_fw.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox_fw.set_homogeneous(True)
        self.flowbox_fw.set_column_spacing(12)
        self.flowbox_fw.set_row_spacing(12)
        self.flowbox_fw.connect("child-activated", self.on_framework_selected)
        
        self.fw_widgets = {}
        for fw in FRAMEWORKS:
            card = self.create_framework_card(fw)
            self.flowbox_fw.add(card)
            self.fw_widgets[fw["id"]] = card
            
        box.pack_start(self.flowbox_fw, False, False, 0)
        
        # DEDICATED DRUPAL VERSION SELECTOR BOX (appears when Drupal is selected)
        self.drupal_version_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.drupal_version_box.get_style_context().add_class("option-highlight-box")
        
        lbl_dp_title = Gtk.Label()
        lbl_dp_title.set_markup("💧 <b>Selecciona la Versión de Drupal:</b>")
        lbl_dp_title.set_halign(Gtk.Align.START)
        self.drupal_version_box.pack_start(lbl_dp_title, False, False, 0)
        
        self.combo_drupal_ver = Gtk.ComboBoxText()
        for dv in DRUPAL_VERSIONS:
            self.combo_drupal_ver.append_text(dv["label"])
        self.combo_drupal_ver.set_active(0)
        self.combo_drupal_ver.connect("changed", self.on_drupal_version_changed)
        self.drupal_version_box.pack_start(self.combo_drupal_ver, False, False, 0)
        
        box.pack_start(self.drupal_version_box, False, False, 0)
        
        # Section 3: Advanced Options Expander
        expander = Gtk.Expander(label="Opciones avanzadas (PHP, Base de datos, etc.)")
        exp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        exp_box.set_margin_top(10)
        exp_box.set_margin_start(16)
        
        grid_adv = Gtk.Grid()
        grid_adv.set_column_spacing(16)
        grid_adv.set_row_spacing(8)
        exp_box.pack_start(grid_adv, False, False, 0)
        
        grid_adv.attach(Gtk.Label(label="Versión de PHP:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.combo_php = Gtk.ComboBoxText()
        for v in ["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]:
            self.combo_php.append_text(v)
        self.combo_php.set_active(0)
        grid_adv.attach(self.combo_php, 1, 0, 1, 1)
        
        grid_adv.attach(Gtk.Label(label="Base de datos:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.combo_db = Gtk.ComboBoxText()
        for db in ["mariadb:10.11", "mysql:8.0", "postgres:16", "mariadb:10.5"]:
            self.combo_db.append_text(db)
        self.combo_db.set_active(0)
        grid_adv.attach(self.combo_db, 1, 1, 1, 1)
        
        grid_adv.attach(Gtk.Label(label="Node.js:", halign=Gtk.Align.END), 0, 2, 1, 1)
        self.combo_node = Gtk.ComboBoxText()
        for n in ["22", "20", "18"]:
            self.combo_node.append_text(n)
        self.combo_node.set_active(0)
        grid_adv.attach(self.combo_node, 1, 2, 1, 1)
        
        self.chk_auto_install = Gtk.CheckButton(label="Ejecutar instalador inicial automático (ej. crear admin/admin en WP/Drupal)")
        self.chk_auto_install.set_active(True)
        exp_box.pack_start(self.chk_auto_install, False, False, 0)
        
        expander.add(exp_box)
        box.pack_start(expander, False, False, 0)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_margin_top(16)
        btn_box.set_halign(Gtk.Align.END)
        
        self.btn_create = Gtk.Button(label="🚀 Crear y Lanzar Proyecto")
        self.btn_create.get_style_context().add_class("btn-primary")
        self.btn_create.connect("clicked", self.on_create_project_clicked)
        btn_box.pack_start(self.btn_create, False, False, 0)
        box.pack_start(btn_box, False, False, 0)
        
        first_child = self.flowbox_fw.get_child_at_index(0)
        if first_child:
            self.flowbox_fw.select_child(first_child)
            self.selected_framework = FRAMEWORKS[0]
            self.drupal_version_box.show()
            
        return scrolled

    def create_framework_card(self, fw):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("framework-card")
        card.fw_data = fw
        
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pixbuf = load_icon(fw["icon"], 36)
        if pixbuf:
            img = Gtk.Image.new_from_pixbuf(pixbuf)
            top_box.pack_start(img, False, False, 0)
            
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<b>{fw['name']}</b>")
        lbl_title.set_halign(Gtk.Align.START)
        title_box.pack_start(lbl_title, False, False, 0)
        
        lbl_cat = Gtk.Label(label=fw["category"])
        lbl_cat.set_halign(Gtk.Align.START)
        lbl_cat.get_style_context().add_class("badge")
        lbl_cat.get_style_context().add_class("badge-tech")
            
        title_box.pack_start(lbl_cat, False, False, 0)
        top_box.pack_start(title_box, True, True, 0)
        card.pack_start(top_box, False, False, 0)
        
        lbl_desc = Gtk.Label(label=fw["desc"])
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_halign(Gtk.Align.START)
        lbl_desc.set_max_width_chars(28)
        lbl_desc.set_opacity(0.8)
        lbl_desc.set_margin_top(4)
        card.pack_start(lbl_desc, True, True, 0)
        
        return card

    def on_framework_selected(self, flowbox, child):
        widget = child.get_child()
        if hasattr(widget, "fw_data"):
            self.selected_framework = widget.fw_data
            fw_id = self.selected_framework["id"]
            
            # Show/hide Drupal version selector
            if fw_id == "drupal":
                self.drupal_version_box.show()
                self.on_drupal_version_changed(self.combo_drupal_ver)
            else:
                self.drupal_version_box.hide()
                php_val = self.selected_framework.get("php", "8.3")
                for idx, text in enumerate(["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]):
                    if text == php_val:
                        self.combo_php.set_active(idx)
                        break

    def on_drupal_version_changed(self, combo):
        idx = combo.get_active()
        if 0 <= idx < len(DRUPAL_VERSIONS):
            ver_info = DRUPAL_VERSIONS[idx]
            target_php = ver_info.get("php", "8.3")
            for p_idx, text in enumerate(["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]):
                if text == target_php:
                    self.combo_php.set_active(p_idx)
                    break

    def on_project_name_changed(self, entry):
        raw_name = entry.get_text().strip()
        slug = re.sub(r'[^a-zA-Z0-9_-]', '-', raw_name).lower()
        base_dir = self.entry_path.get_text().strip()
        final_path = os.path.join(base_dir, slug if slug else "")
        self.lbl_path_preview.set_markup(f"<small>Carpeta final: <tt>{final_path}</tt></small>")

    def on_browse_folder(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar carpeta de proyectos",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_current_folder(self.entry_path.get_text().strip())
        if dialog.run() == Gtk.ResponseType.OK:
            self.entry_path.set_text(dialog.get_filename())
            self.on_project_name_changed(self.entry_name)
        dialog.destroy()

    def build_tab_projects(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        vbox.set_margin_top(14)
        vbox.set_margin_bottom(14)
        
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar proyecto por nombre o tipo...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)
        vbox.pack_start(search_box, False, False, 0)
        
        self.projects_scrolled = Gtk.ScrolledWindow()
        self.projects_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.projects_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.projects_scrolled.add(self.projects_list_box)
        vbox.pack_start(self.projects_scrolled, True, True, 0)
        
        return vbox

    def refresh_projects(self):
        for child in self.projects_list_box.get_children():
            self.projects_list_box.remove(child)
            
        loading_lbl = Gtk.Label(label="Cargando proyectos de DDEV...")
        self.projects_list_box.pack_start(loading_lbl, True, True, 20)
        self.projects_list_box.show_all()
        
        def run_list():
            try:
                res = subprocess.run(["ddev", "list", "-j"], capture_output=True, text=True, timeout=15)
                raw_json = res.stdout.strip()
                if raw_json:
                    data = json.loads(raw_json)
                    projects = data.get("raw", [])
                else:
                    projects = []
            except Exception:
                projects = []
            GLib.idle_add(self.update_projects_ui, projects)
            
        threading.Thread(target=run_list, daemon=True).start()

    def update_projects_ui(self, projects):
        for child in self.projects_list_box.get_children():
            self.projects_list_box.remove(child)
            
        self.lbl_proj_title.set_text(f"Mis Proyectos ({len(projects)})")
        
        if not projects:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            empty_box.set_margin_top(40)
            
            icon = Gtk.Image.new_from_icon_name("folder-saved-search-symbolic", Gtk.IconSize.DIALOG)
            empty_box.pack_start(icon, False, False, 0)
            
            lbl_empty = Gtk.Label()
            lbl_empty.set_markup("<b>No hay proyectos de DDEV activos</b>\nCrea uno nuevo desde la pestaña <i>'Nuevo Proyecto'</i>.")
            lbl_empty.set_justify(Gtk.Justification.CENTER)
            empty_box.pack_start(lbl_empty, False, False, 0)
            
            self.projects_list_box.pack_start(empty_box, True, True, 0)
            self.projects_list_box.show_all()
            return
            
        for proj in projects:
            card = self.create_project_item(proj)
            self.projects_list_box.pack_start(card, False, False, 0)
            
        self.projects_list_box.show_all()

    def create_project_item(self, proj):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        card.get_style_context().add_class("project-card")
        card.project_data = proj
        
        ptype = proj.get("type", "").lower()
        icon_name = "php.svg"
        if "wordpress" in ptype:
            icon_name = "wordpress.svg"
        elif "drupal" in ptype:
            icon_name = "drupal.svg"
        elif "laravel" in ptype:
            icon_name = "laravel.svg"
        elif "react" in ptype or "vite" in ptype or "generic" in ptype:
            icon_name = "react.svg"
        elif "vue" in ptype:
            icon_name = "vue.svg"
        elif "symfony" in ptype:
            icon_name = "symfony.svg"
            
        pixbuf = load_icon(icon_name, 40)
        if pixbuf:
            img = Gtk.Image.new_from_pixbuf(pixbuf)
            card.pack_start(img, False, False, 0)
            
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)
        
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_name = Gtk.Label()
        lbl_name.set_markup(f"<b>{proj.get('name', 'Sin nombre')}</b>")
        title_row.pack_start(lbl_name, False, False, 0)
        
        status = proj.get("status", "").lower()
        lbl_status = Gtk.Label(label=status.upper())
        lbl_status.get_style_context().add_class("badge")
        if "running" in status or "ok" in status:
            lbl_status.get_style_context().add_class("badge-running")
        elif "paused" in status:
            lbl_status.get_style_context().add_class("badge-paused")
        else:
            lbl_status.get_style_context().add_class("badge-stopped")
        title_row.pack_start(lbl_status, False, False, 0)
        
        lbl_type = Gtk.Label(label=proj.get("type", "generic"))
        lbl_type.get_style_context().add_class("badge")
        lbl_type.get_style_context().add_class("badge-tech")
        title_row.pack_start(lbl_type, False, False, 0)
        
        info_box.pack_start(title_row, False, False, 0)
        
        primary_url = proj.get("primary_url") or proj.get("httpsurl") or proj.get("httpurl") or ""
        lbl_url = Gtk.Label()
        if primary_url:
            lbl_url.set_markup(f"<a href='{primary_url}'>{primary_url}</a>")
        else:
            lbl_url.set_text("Sin URL activa")
        lbl_url.set_halign(Gtk.Align.START)
        info_box.pack_start(lbl_url, False, False, 0)
        
        approot = proj.get("approot", "")
        lbl_path = Gtk.Label()
        lbl_path.set_markup(f"<small><span opacity='0.7'>{approot}</span></small>")
        lbl_path.set_halign(Gtk.Align.START)
        info_box.pack_start(lbl_path, False, False, 0)
        
        card.pack_start(info_box, True, True, 0)
        
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions_box.set_valign(Gtk.Align.CENTER)
        
        is_running = "running" in status or "ok" in status
        
        btn_toggle = Gtk.Button()
        if is_running:
            btn_toggle.set_label("⏹ Detener")
            btn_toggle.set_tooltip_text("Detener proyecto (ddev stop)")
            btn_toggle.connect("clicked", lambda b, p=proj: self.execute_simple_action("stop", p))
        else:
            btn_toggle.set_label("▶ Iniciar")
            btn_toggle.get_style_context().add_class("btn-primary")
            btn_toggle.set_tooltip_text("Iniciar proyecto (ddev start)")
            btn_toggle.connect("clicked", lambda b, p=proj: self.execute_simple_action("start", p))
        actions_box.pack_start(btn_toggle, False, False, 0)
        
        if primary_url:
            btn_web = Gtk.Button()
            btn_web.add(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.BUTTON))
            btn_web.set_tooltip_text("Abrir en navegador web")
            btn_web.connect("clicked", lambda b, url=primary_url: webbrowser.open(url))
            actions_box.pack_start(btn_web, False, False, 0)
            
        if approot and os.path.exists(approot):
            btn_folder = Gtk.Button()
            btn_folder.add(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON))
            btn_folder.set_tooltip_text("Abrir carpeta en gestor de archivos")
            btn_folder.connect("clicked", lambda b, path=approot: subprocess.Popen(["xdg-open", path]))
            actions_box.pack_start(btn_folder, False, False, 0)
            
        if approot and os.path.exists(approot):
            btn_term = Gtk.Button()
            btn_term.add(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON))
            btn_term.set_tooltip_text("Abrir terminal en esta carpeta")
            btn_term.connect("clicked", lambda b, path=approot: self.open_terminal(path))
            actions_box.pack_start(btn_term, False, False, 0)
            
        btn_del = Gtk.Button()
        btn_del.add(Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON))
        btn_del.set_tooltip_text("Eliminar proyecto DDEV")
        btn_del.connect("clicked", lambda b, p=proj: self.confirm_delete_project(p))
        actions_box.pack_start(btn_del, False, False, 0)
        
        card.pack_start(actions_box, False, False, 0)
        return card

    def open_terminal(self, path):
        for term in ["mate-terminal", "gnome-terminal", "x-terminal-emulator", "xterm"]:
            if shutil.which(term):
                if term in ["mate-terminal", "gnome-terminal"]:
                    subprocess.Popen([term, f"--working-directory={path}"])
                else:
                    subprocess.Popen([term], cwd=path)
                return

    def on_search_changed(self, entry):
        query = entry.get_text().strip().lower()
        for child in self.projects_list_box.get_children():
            if hasattr(child, "project_data"):
                p = child.project_data
                name = p.get("name", "").lower()
                ptype = p.get("type", "").lower()
                url = p.get("primary_url", "").lower()
                match = (query in name) or (query in ptype) or (query in url)
                child.set_visible(match)

    def execute_simple_action(self, action, proj):
        approot = proj.get("approot", "")
        pname = proj.get("name", "")
        
        dialog = ProgressDialog(self, title=f"{action.capitalize()} {pname}")
        dialog.set_status(f"Ejecutando ddev {action} en {pname}...")
        
        def task():
            cmd = ["ddev"] + action.split()
            process = subprocess.Popen(
                cmd,
                cwd=approot,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in iter(process.stdout.readline, ''):
                if line:
                    GLib.idle_add(dialog.append_log, line)
            process.stdout.close()
            process.wait()
            success = (process.returncode == 0)
            url = proj.get("primary_url", "") if "start" in action else ""
            msg = f"Proyecto {pname} {action} con éxito" if success else f"Error al ejecutar {action}"
            GLib.idle_add(dialog.finish, success, msg, url, approot)
            GLib.idle_add(self.refresh_projects)
            
        threading.Thread(target=task, daemon=True).start()

    def confirm_delete_project(self, proj):
        pname = proj.get("name", "")
        approot = proj.get("approot", "")
        
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"¿Estás seguro de eliminar '{pname}'?"
        )
        dialog.format_secondary_text(
            f"Se detendrán y eliminarán los contenedores y base de datos de DDEV.\nUbicación: {approot}\n\nNota: Los archivos de tu código fuente permanecerán seguros."
        )
        res = dialog.run()
        dialog.destroy()
        
        if res == Gtk.ResponseType.OK:
            self.execute_simple_action("delete -O", proj)

    def build_tab_tools(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(20)
        box.set_margin_bottom(24)
        
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<b>Herramientas Globales de DDEV</b>")
        lbl_title.set_halign(Gtk.Align.START)
        box.pack_start(lbl_title, False, False, 0)
        
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)
        box.pack_start(grid, False, False, 0)
        
        btn_stop_all = Gtk.Button(label="⏹ Detener Todos los Proyectos (Poweroff)")
        btn_stop_all.connect("clicked", self.on_global_poweroff)
        grid.attach(btn_stop_all, 0, 0, 1, 1)
        
        btn_start_all = Gtk.Button(label="▶ Iniciar Todos los Proyectos")
        btn_start_all.connect("clicked", self.on_global_start_all)
        grid.attach(btn_start_all, 1, 0, 1, 1)
        
        btn_clean = Gtk.Button(label="🧹 Limpiar Caché e Imágenes Huérfanas")
        btn_clean.connect("clicked", self.on_clean_ddev)
        grid.attach(btn_clean, 0, 1, 1, 1)
        
        btn_router = Gtk.Button(label="🌐 Abrir Panel Traefik Router")
        btn_router.connect("clicked", lambda b: webbrowser.open("http://127.0.0.1:10999"))
        grid.attach(btn_router, 1, 1, 1, 1)
        
        info_frame = Gtk.Frame(label=" Estado del Sistema ")
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_margin_start(12)
        info_box.set_margin_end(12)
        info_box.set_margin_top(12)
        info_box.set_margin_bottom(12)
        
        self.lbl_system_info = Gtk.Label()
        self.lbl_system_info.set_halign(Gtk.Align.START)
        self.lbl_system_info.set_line_wrap(True)
        info_box.pack_start(self.lbl_system_info, False, False, 0)
        info_frame.add(info_box)
        box.pack_start(info_frame, False, False, 0)
        
        self.update_system_info()
        return box

    def update_system_info(self):
        def task():
            try:
                v = subprocess.run(["ddev", "--version"], capture_output=True, text=True).stdout.strip()
                dock = subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.strip()
                info_text = f"• <b>DDEV:</b> {v}\n• <b>Docker:</b> {dock}\n• <b>Directorio predeterminado:</b> {DEFAULT_SITES_DIR}"
            except Exception as e:
                info_text = f"Error obteniendo estado: {e}"
            GLib.idle_add(lambda: self.lbl_system_info.set_markup(info_text))
        threading.Thread(target=task, daemon=True).start()

    def on_global_poweroff(self, widget):
        dialog = ProgressDialog(self, title="Deteniendo DDEV")
        dialog.set_status("Deteniendo todos los contenedores...")
        def task():
            p = subprocess.Popen(["ddev", "poweroff"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(p.stdout.readline, ''):
                GLib.idle_add(dialog.append_log, line)
            p.stdout.close()
            p.wait()
            GLib.idle_add(dialog.finish, p.returncode == 0, "Todos los proyectos se detuvieron correctamente")
            GLib.idle_add(self.refresh_projects)
        threading.Thread(target=task, daemon=True).start()

    def on_global_start_all(self, widget):
        dialog = ProgressDialog(self, title="Iniciando Proyectos")
        dialog.set_status("Iniciando todos los proyectos...")
        def task():
            p = subprocess.Popen(["ddev", "start", "-a"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(p.stdout.readline, ''):
                GLib.idle_add(dialog.append_log, line)
            p.stdout.close()
            p.wait()
            GLib.idle_add(dialog.finish, p.returncode == 0, "Proyectos iniciados")
            GLib.idle_add(self.refresh_projects)
        threading.Thread(target=task, daemon=True).start()

    def on_clean_ddev(self, widget):
        dialog = ProgressDialog(self, title="Limpiando DDEV")
        dialog.set_status("Ejecutando ddev clean...")
        def task():
            p = subprocess.Popen(["ddev", "clean", "-y"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(p.stdout.readline, ''):
                GLib.idle_add(dialog.append_log, line)
            p.stdout.close()
            p.wait()
            GLib.idle_add(dialog.finish, p.returncode == 0, "Limpieza completada")
            GLib.idle_add(self.refresh_projects)
        threading.Thread(target=task, daemon=True).start()

    def on_show_about(self, widget):
        about = Gtk.AboutDialog(transient_for=self, modal=True)
        about.set_program_name("DDEV Studio")
        about.set_version("1.2.0")
        about.set_comments("Gestor visual de proyectos DDEV para Ubuntu MATE.\nCrea proyectos de Drupal (11/10/9/8/7), WordPress, Laravel, React, Vue y más con 1 clic.")
        about.set_website("https://ddev.readthedocs.io")
        about.set_website_label("Documentación Oficial de DDEV")
        ddev_icon = load_icon("ddev.svg", 64)
        if ddev_icon:
            about.set_logo(ddev_icon)
        about.run()
        about.destroy()

    def on_create_project_clicked(self, widget):
        raw_name = self.entry_name.get_text().strip()
        slug = re.sub(r'[^a-zA-Z0-9_-]', '-', raw_name).lower()
        if not slug:
            msg_diag = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Por favor ingresa un nombre para el proyecto"
            )
            msg_diag.run()
            msg_diag.destroy()
            self.entry_name.grab_focus()
            return
            
        base_dir = self.entry_path.get_text().strip()
        target_dir = os.path.join(base_dir, slug)
        
        clean_target_before = False
        if os.path.exists(target_dir) and os.listdir(target_dir):
            msg_diag = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text=f"La carpeta '{slug}' ya existe y contiene archivos."
            )
            msg_diag.format_secondary_text(
                "Para evitar errores de Composer o Vite, se recomienda vaciar la carpeta para un proyecto limpio.\n¿Cómo deseas proceder?"
            )
            msg_diag.add_button("Cancelar", Gtk.ResponseType.CANCEL)
            msg_diag.add_button("Mantener archivos", Gtk.ResponseType.NO)
            msg_diag.add_button("🧹 Vaciar y Crear Limpio (Recomendado)", Gtk.ResponseType.YES)
            
            res = msg_diag.run()
            msg_diag.destroy()
            
            if res == Gtk.ResponseType.CANCEL or res == Gtk.ResponseType.DELETE_EVENT:
                return
            elif res == Gtk.ResponseType.YES:
                clean_target_before = True

        fw = getattr(self, "selected_framework", FRAMEWORKS[0])
        fw_id = fw["id"]
        
        # Determine Drupal version details if Drupal is selected
        drupal_ver_info = DRUPAL_VERSIONS[0]
        if fw_id == "drupal":
            idx = self.combo_drupal_ver.get_active()
            if 0 <= idx < len(DRUPAL_VERSIONS):
                drupal_ver_info = DRUPAL_VERSIONS[idx]

        php_version = self.combo_php.get_active_text() or fw.get("php", "8.3")
        db_type = self.combo_db.get_active_text() or fw.get("db", "mariadb:10.11")
        node_version = self.combo_node.get_active_text() or "22"
        auto_install = self.chk_auto_install.get_active()
        
        dialog_title = f"Creando {fw['name']}"
        if fw_id == "drupal":
            dialog_title = f"Creando Drupal {drupal_ver_info['id']}: {slug}"
        else:
            dialog_title = f"Creando {fw['name']}: {slug}"
            
        dialog = ProgressDialog(self, title=dialog_title)
        dialog.set_status(f"Iniciando creación de {dialog_title}...")
        
        def run_creation():
            try:
                def log(text):
                    GLib.idle_add(dialog.append_log, text + "\n")
                    
                def set_st(st):
                    GLib.idle_add(dialog.set_status, st)
                    
                set_st("Limpiando contenedores anteriores si existen...")
                subprocess.run(["ddev", "delete", "-O", "-y", slug], capture_output=True)
                
                if clean_target_before and os.path.exists(target_dir):
                    set_st("Vaciando carpeta de proyecto...")
                    shutil.rmtree(target_dir, ignore_errors=True)
                    
                os.makedirs(target_dir, exist_ok=True)
                
                log(f"📁 Directorio del proyecto: {target_dir}")
                log(f"🚀 Tecnología: {fw['name']}" + (f" (Versión {drupal_ver_info['id']})" if fw_id == 'drupal' else ""))
                log(f"🐘 Versión de PHP: {php_version} | DB: {db_type}\n" + "="*50)
                
                primary_url = f"https://{slug}.ddev.site"
                
                if fw_id == "drupal":
                    d_ver = drupal_ver_info["id"]
                    d_type = drupal_ver_info["type"]
                    d_docroot = drupal_ver_info["docroot"]
                    
                    set_st(f"Configurando DDEV para Drupal {d_ver}...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        f"--project-type={d_type}",
                        f"--docroot={d_docroot}",
                        f"--php-version={php_version}",
                        f"--database={db_type}"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    set_st("Levantando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    if d_ver in ["11", "10", "9"]:
                        set_st(f"Descargando Drupal {d_ver} con Composer...")
                        self.run_subproc(["ddev", "composer", "create-project", f"drupal/recommended-project:^{d_ver}"], target_dir, dialog)
                        
                        set_st("Instalando Drush...")
                        self.run_subproc(["ddev", "composer", "require", "drush/drush"], target_dir, dialog)
                        
                        if auto_install:
                            set_st(f"Instalando perfil estándar de Drupal {d_ver}...")
                            inst_cmd = [
                                "ddev", "drush", "site:install", "standard",
                                "--account-name=admin",
                                "--account-pass=admin",
                                f"--site-name={slug.capitalize()}",
                                "-y"
                            ]
                            self.run_subproc(inst_cmd, target_dir, dialog)
                            log(f"\n🎉 Drupal {d_ver} instalado con éxito!")
                            log("Credenciales: admin / admin")
                            
                    elif d_ver == "8":
                        set_st("Descargando Drupal 8 con Composer...")
                        self.run_subproc(["ddev", "composer", "create-project", "drupal/recommended-project:^8"], target_dir, dialog)
                        
                        set_st("Instalando Drush 10...")
                        self.run_subproc(["ddev", "composer", "require", "drush/drush:^10"], target_dir, dialog)
                        
                        if auto_install:
                            set_st("Instalando perfil estándar de Drupal 8...")
                            inst_cmd = [
                                "ddev", "drush", "site:install", "standard",
                                "--account-name=admin",
                                "--account-pass=admin",
                                f"--site-name={slug.capitalize()}",
                                "-y"
                            ]
                            self.run_subproc(inst_cmd, target_dir, dialog)
                            log("\n🎉 Drupal 8 instalado con éxito!")
                            log("Credenciales: admin / admin")
                            
                    elif d_ver == "7":
                        set_st("Descargando Drupal 7...")
                        self.run_subproc(["ddev", "drush", "dl", "drupal-7", "-y", "--destination=/tmp/d7"], target_dir, dialog)
                        self.run_subproc(["ddev", "exec", "sh -c 'cp -a /tmp/d7/drupal-7*/* /var/www/html/ && cp -a /tmp/d7/drupal-7*/.* /var/www/html/ 2>/dev/null || true; rm -rf /tmp/d7'"], target_dir, dialog)
                        
                        if auto_install:
                            set_st("Instalando Drupal 7 estándar...")
                            inst_cmd = [
                                "ddev", "drush", "site:install", "standard",
                                "--account-name=admin",
                                "--account-pass=admin",
                                f"--site-name={slug.capitalize()}",
                                "-y"
                            ]
                            self.run_subproc(inst_cmd, target_dir, dialog)
                            log("\n🎉 Drupal 7 instalado con éxito!")
                            log("Credenciales: admin / admin")

                elif fw_id == "wordpress":
                    set_st("Configurando DDEV para WordPress...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=wordpress",
                        "--docroot=.",
                        f"--php-version={php_version}",
                        f"--database={db_type}"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    set_st("Levantando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    set_st("Descargando núcleo de WordPress...")
                    self.run_subproc(["ddev", "wp", "core", "download"], target_dir, dialog)
                    
                    if auto_install:
                        set_st("Instalando base de datos y usuario admin...")
                        install_cmd = [
                            "ddev", "wp", "core", "install",
                            f"--url=https://{slug}.ddev.site",
                            f"--title={slug.capitalize()}",
                            "--admin_user=admin",
                            "--admin_password=admin",
                            "--admin_email=admin@example.com",
                            "--skip-email"
                        ]
                        self.run_subproc(install_cmd, target_dir, dialog)
                        log("\n🎉 WordPress instalado!")
                        log("Credenciales: admin / admin")

                elif fw_id == "laravel":
                    set_st("Configurando DDEV para Laravel...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=laravel",
                        "--docroot=public",
                        f"--php-version={php_version}",
                        f"--database={db_type}"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    set_st("Levantando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    set_st("Instalando Laravel con Composer...")
                    self.run_subproc(["ddev", "composer", "create-project", "--prefer-dist", "laravel/laravel"], target_dir, dialog)
                    
                    set_st("Generando clave de aplicación...")
                    self.run_subproc(["ddev", "exec", "php artisan key:generate"], target_dir, dialog)
                    log("\n🎉 Laravel instalado con éxito!")

                elif fw_id == "react":
                    set_st("Configurando DDEV para React...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=generic",
                        "--docroot=dist",
                        f"--nodejs-version={node_version}",
                        f"--database={db_type}"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    try:
                        cfg_yaml = os.path.join(target_dir, ".ddev", "config.yaml")
                        if os.path.exists(cfg_yaml):
                            with open(cfg_yaml, "a") as f:
                                f.write("\nweb_extra_exposed_ports:\n  - name: nodejs\n    container_port: 5173\n    http_port: 5172\n    https_port: 5173\n")
                    except Exception:
                        pass
                    
                    set_st("Levantando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    set_st("Creando plantilla React con Vite...")
                    self.run_subproc(["ddev", "npx", "--yes", "create-vite@latest", "tmp-vite", "--template", "react-ts"], target_dir, dialog)
                    
                    set_st("Organizando estructura del proyecto...")
                    self.run_subproc(["ddev", "exec", "sh -c 'cp -a tmp-vite/. . && rm -rf tmp-vite'"], target_dir, dialog)
                    self.run_subproc(["ddev", "exec", "sed -i 's/\"dev\": \"vite\"/\"dev\": \"vite --host 0.0.0.0\"/g' package.json"], target_dir, dialog)
                    
                    set_st("Instalando dependencias npm...")
                    self.run_subproc(["ddev", "npm", "install"], target_dir, dialog)
                    
                    set_st("Compilando versión inicial...")
                    self.run_subproc(["ddev", "npm", "run", "build"], target_dir, dialog)
                    log("\n🎉 Proyecto React listo!")

                elif fw_id == "vue":
                    set_st("Configurando DDEV para Vue 3...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=generic",
                        "--docroot=dist",
                        f"--nodejs-version={node_version}",
                        f"--database={db_type}"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    try:
                        cfg_yaml = os.path.join(target_dir, ".ddev", "config.yaml")
                        if os.path.exists(cfg_yaml):
                            with open(cfg_yaml, "a") as f:
                                f.write("\nweb_extra_exposed_ports:\n  - name: nodejs\n    container_port: 5173\n    http_port: 5172\n    https_port: 5173\n")
                    except Exception:
                        pass
                    
                    set_st("Levantando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    set_st("Creando plantilla Vue 3 con Vite...")
                    self.run_subproc(["ddev", "npx", "--yes", "create-vite@latest", "tmp-vite", "--template", "vue-ts"], target_dir, dialog)
                    
                    set_st("Organizando estructura del proyecto...")
                    self.run_subproc(["ddev", "exec", "sh -c 'cp -a tmp-vite/. . && rm -rf tmp-vite'"], target_dir, dialog)
                    self.run_subproc(["ddev", "exec", "sed -i 's/\"dev\": \"vite\"/\"dev\": \"vite --host 0.0.0.0\"/g' package.json"], target_dir, dialog)
                    
                    set_st("Instalando dependencias npm...")
                    self.run_subproc(["ddev", "npm", "install"], target_dir, dialog)
                    
                    set_st("Compilando versión inicial...")
                    self.run_subproc(["ddev", "npm", "run", "build"], target_dir, dialog)
                    log("\n🎉 Proyecto Vue listo!")

                elif fw_id == "symfony":
                    set_st("Configurando DDEV para Symfony...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=php",
                        "--docroot=public",
                        f"--php-version={php_version}",
                        f"--database={db_type}"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    set_st("Levantando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    set_st("Descargando Symfony...")
                    self.run_subproc(["ddev", "composer", "create-project", "symfony/skeleton", "."], target_dir, dialog)
                    self.run_subproc(["ddev", "composer", "require", "webapp"], target_dir, dialog)
                    log("\n🎉 Proyecto Symfony listo!")

                else:  # Generic PHP
                    set_st("Configurando DDEV PHP...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=php",
                        "--docroot=.",
                        f"--php-version={php_version}",
                        f"--database={db_type}"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    index_path = os.path.join(target_dir, "index.php")
                    if not os.path.exists(index_path):
                        with open(index_path, "w") as f:
                            f.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{slug} - DDEV Studio</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 500px; }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        .badge {{ background: #0284c7; padding: 4px 12px; border-radius: 9999px; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>¡Proyecto {slug} Activo! 🚀</h1>
        <p>Tu entorno DDEV está corriendo perfectamente en Ubuntu MATE.</p>
        <p><span class="badge">PHP <?php echo phpversion(); ?></span></p>
    </div>
</body>
</html>""")
                    
                    set_st("Levantando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    log("\n🎉 Proyecto PHP listo!")

                log("\n" + "="*50)
                log(f"URL: {primary_url}")
                log("¡Completado con éxito!")
                GLib.idle_add(dialog.finish, True, f"¡Proyecto '{slug}' creado con éxito!", primary_url, target_dir)
                GLib.idle_add(self.refresh_projects)
                
            except Exception as e:
                log(f"\n❌ ERROR: {str(e)}")
                GLib.idle_add(dialog.finish, False, f"Error en la creación: {str(e)}", "", target_dir)
                
        threading.Thread(target=run_creation, daemon=True).start()

    def run_subproc(self, cmd, cwd, dialog):
        cmd_str = " ".join(cmd)
        GLib.idle_add(dialog.append_log, f"\n$ {cmd_str}\n")
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in iter(proc.stdout.readline, ''):
            if line:
                GLib.idle_add(dialog.append_log, line)
        proc.stdout.close()
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"El comando falló con código {proc.returncode}: {cmd_str}")


def main():
    app = DDEVManagerWindow()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
