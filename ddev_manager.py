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
.segmented-btn {
    border-radius: 8px;
    padding: 6px 16px;
    font-weight: bold;
}
.segmented-btn:checked {
    background-color: #0284c7;
    color: white;
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
.badge-multisite {
    background-color: #8b5cf6;
    color: white;
    font-weight: bold;
}
.badge-single-site {
    background-color: #0284c7;
    color: white;
    font-weight: 500;
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
.btn-drupal {
    background-color: alpha(#0678be, 0.15);
    color: @theme_text_color;
    border: 1px solid alpha(#0678be, 0.4);
    border-radius: 6px;
    padding: 3px 8px;
    font-weight: 500;
}
.btn-drupal:hover {
    background-color: alpha(#0678be, 0.3);
    border-color: #0678be;
}
.btn-quick {
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: bold;
}
.btn-quick-cache {
    background-color: alpha(#10b981, 0.15);
    color: @theme_text_color;
    border: 1px solid alpha(#10b981, 0.4);
}
.btn-quick-cache:hover {
    background-color: alpha(#10b981, 0.3);
    border-color: #10b981;
}
.btn-quick-login {
    background-color: alpha(#f59e0b, 0.15);
    color: @theme_text_color;
    border: 1px solid alpha(#f59e0b, 0.4);
}
.btn-quick-login:hover {
    background-color: alpha(#f59e0b, 0.3);
    border-color: #f59e0b;
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
        "id": "django",
        "name": "Django",
        "category": "Python Framework",
        "desc": "Framework web de alto nivel en Python con ORM, admin y base de datos.",
        "icon": "django.svg",
        "php": "8.3",
        "docroot": ".",
        "db": "postgres:16",
    },
    {
        "id": "flask",
        "name": "Flask",
        "category": "Python Microframework",
        "desc": "Microframework ligero y flexible en Python para APIs y aplicaciones web.",
        "icon": "flask.svg",
        "php": "8.3",
        "docroot": ".",
        "db": "mariadb:10.11",
    },
    {
        "id": "angular",
        "name": "Angular",
        "category": "Frontend SPA",
        "desc": "Plataforma y framework TypeScript de Google para aplicaciones web escalables.",
        "icon": "angular.svg",
        "php": "8.2",
        "docroot": "dist",
        "db": "mariadb:10.11",
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



def detect_project_details(folder_path):
    """
    Analyzes a directory and detects framework type, docroot, php/node version, and database.
    """
    if not folder_path or not os.path.exists(folder_path):
        return {
            "name": "",
            "type": "drupal10",
            "docroot": "docroot",
            "php": "8.3",
            "nodejs": "22",
            "db": "mariadb:10.11",
            "is_drupal": True,
            "is_multisite": True,
            "summary": "Directorio no encontrado",
            "valid": False
        }
        
    pname = os.path.basename(folder_path.rstrip("/"))
    slug = re.sub(r'[^a-zA-Z0-9_-]', '-', pname).lower()
    
    # 1. Detect Docroot
    docroot = "."
    for dr in ["docroot", "web", "public", "dist"]:
        if os.path.isdir(os.path.join(folder_path, dr)):
            docroot = dr
            break
            
    # 2. Check if .ddev/config.yaml exists
    ddev_cfg = os.path.join(folder_path, ".ddev", "config.yaml")
    if os.path.exists(ddev_cfg):
        try:
            with open(ddev_cfg, "r") as f:
                content = f.read()
            m_name = re.search(r'^name:\s*([^\s]+)', content, re.MULTILINE)
            m_type = re.search(r'^type:\s*([^\s]+)', content, re.MULTILINE)
            m_docroot = re.search(r'^docroot:\s*([^\s]+)', content, re.MULTILINE)
            m_php = re.search(r'^php_version:\s*([^\s]+)', content, re.MULTILINE)
            m_node = re.search(r'^nodejs_version:\s*([^\s]+)', content, re.MULTILINE)
            m_db = re.search(r'^database:\s*\n\s*type:\s*([^\s]+)', content, re.MULTILINE)
            
            p_type = m_type.group(1).strip().strip('"\'') if m_type else "drupal10"
            if m_name:
                slug = m_name.group(1).strip().strip('"\'')
            if m_docroot:
                docroot = m_docroot.group(1).strip().strip('"\'')
            php_v = m_php.group(1).strip().strip('"\'') if m_php else "8.3"
            node_v = m_node.group(1).strip().strip('"\'') if m_node else "22"
            db_v = m_db.group(1).strip().strip('"\'') if m_db else "mariadb:10.11"
            if "omit_containers" in content and "db" in content:
                db_v = "none"
            
            is_dr = "drupal" in p_type
            return {
                "name": slug,
                "type": p_type,
                "docroot": docroot,
                "php": php_v,
                "nodejs": node_v,
                "db": db_v,
                "is_drupal": is_dr,
                "is_multisite": is_dr,
                "summary": f"Configuración DDEV detectada ({p_type}, docroot: {docroot})",
                "valid": True
            }
        except Exception:
            pass

    # 3. Check composer.json
    composer_file = os.path.join(folder_path, "composer.json")
    if os.path.exists(composer_file):
        try:
            with open(composer_file, "r") as f:
                cdata = json.load(f)
            req = cdata.get("require", {})
            req_dev = cdata.get("require-dev", {})
            all_req = {**req, **req_dev}
            
            for k, v in all_req.items():
                if "drupal/core" in k:
                    if "11" in str(v):
                        return {"name": slug, "type": "drupal11", "docroot": docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Drupal 11 detectado (docroot: {docroot})", "valid": True}
                    elif "9" in str(v):
                        return {"name": slug, "type": "drupal9", "docroot": docroot, "php": "8.1", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Drupal 9 detectado (docroot: {docroot})", "valid": True}
                    elif "8" in str(v):
                        return {"name": slug, "type": "drupal8", "docroot": docroot, "php": "7.4", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Drupal 8 detectado (docroot: {docroot})", "valid": True}
                    else:
                        return {"name": slug, "type": "drupal10", "docroot": docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Drupal 10 detectado (docroot: {docroot})", "valid": True}
                        
            if "laravel/framework" in all_req:
                return {"name": slug, "type": "laravel", "docroot": "public" if os.path.exists(os.path.join(folder_path, "public")) else docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "Laravel detectado", "valid": True}
            if "symfony/" in str(all_req):
                return {"name": slug, "type": "symfony", "docroot": "public" if os.path.exists(os.path.join(folder_path, "public")) else docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "Symfony detectado", "valid": True}
            if "roots/bedrock" in all_req or "wordpress" in str(all_req):
                return {"name": slug, "type": "wordpress", "docroot": docroot, "php": "8.2", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "WordPress (Composer) detectado", "valid": True}
        except Exception:
            pass

    # 4. Check filesystem structures
    if os.path.exists(os.path.join(folder_path, docroot, "sites")) or os.path.exists(os.path.join(folder_path, "sites", "default")):
        return {"name": slug, "type": "drupal10", "docroot": docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Estructura Drupal detectada (docroot: {docroot})", "valid": True}
    if os.path.exists(os.path.join(folder_path, "wp-config.php")) or os.path.exists(os.path.join(folder_path, "wp-content")):
        return {"name": slug, "type": "wordpress", "docroot": ".", "php": "8.2", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "WordPress detectado", "valid": True}
    if os.path.exists(os.path.join(folder_path, "artisan")):
        return {"name": slug, "type": "laravel", "docroot": "public", "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "Laravel detectado", "valid": True}
    if os.path.exists(os.path.join(folder_path, "angular.json")):
        return {"name": slug, "type": "angular", "docroot": "dist", "php": "8.2", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Angular detectado (Node.js/Vite)", "valid": True}
    if os.path.exists(os.path.join(folder_path, "manage.py")):
        return {"name": slug, "type": "django", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "postgres:16", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Django detectado (Python 3)", "valid": True}
    if os.path.exists(os.path.join(folder_path, "app.py")) or os.path.exists(os.path.join(folder_path, "wsgi.py")):
        return {"name": slug, "type": "flask", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Flask detectado (Python 3)", "valid": True}

    if os.path.exists(os.path.join(folder_path, "package.json")) and not os.path.exists(os.path.join(folder_path, "composer.json")):
        try:
            with open(os.path.join(folder_path, "package.json"), "r") as pf:
                pdata = json.load(pf)
            all_deps = {**pdata.get("dependencies", {}), **pdata.get("devDependencies", {})}
            if "react" in all_deps:
                return {"name": slug, "type": "react", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto React detectado (Vite/Node)", "valid": True}
            if "vue" in all_deps:
                return {"name": slug, "type": "vue", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Vue detectado (Vite/Node)", "valid": True}
        except Exception:
            pass
        return {"name": slug, "type": "generic", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Node.js / Frontend detectado", "valid": True}

    return {
        "name": slug,
        "type": "php",
        "docroot": docroot,
        "php": "8.3",
        "nodejs": "22",
        "db": "mariadb:10.11",
        "is_drupal": False,
        "is_multisite": False,
        "summary": f"Proyecto PHP estándar (docroot: {docroot})",
        "valid": True
    }


class SubsitesManagerDialog(Gtk.Dialog):
    def __init__(self, parent, proj, main_app):
        pname = proj.get("name", "Proyecto Drupal")
        super().__init__(title=f"💧 Drupal Multisite: {pname}", transient_for=parent, flags=Gtk.DialogFlags.MODAL)
        self.set_default_size(960, 720)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.proj = proj
        self.main_app = main_app
        self.base_dir = proj.get("approot", "")
        self.base_name = pname
        self.subsites = []
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        
        # 1. Header Box (Project Summary & Controls)
        header_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        header_card.get_style_context().add_class("option-highlight-box")
        
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        pix_dp = load_icon("drupal.svg", 36)
        if pix_dp:
            top_row.pack_start(Gtk.Image.new_from_pixbuf(pix_dp), False, False, 0)
            
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<big><b>{pname}</b></big> <span color='#8b5cf6'><b>[DRUPAL MULTISITE]</b></span>")
        lbl_title.set_halign(Gtk.Align.START)
        title_box.pack_start(lbl_title, False, False, 0)
        
        lbl_path = Gtk.Label()
        lbl_path.set_markup(f"<small><span color='#94a3b8'>📁 <b>Ubicación:</b> {self.base_dir}</span></small>")
        lbl_path.set_halign(Gtk.Align.START)
        title_box.pack_start(lbl_path, False, False, 0)
        top_row.pack_start(title_box, True, True, 0)
        
        header_card.pack_start(top_row, False, False, 0)
        
        # Controls row
        ctrl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_base_info = Gtk.Label()
        self.lbl_base_info.set_halign(Gtk.Align.START)
        self.lbl_base_info.set_hexpand(True)
        ctrl_row.pack_start(self.lbl_base_info, True, True, 0)
        
        self.btn_base_start = Gtk.Button(label="▶ Iniciar DDEV")
        self.btn_base_start.get_style_context().add_class("btn-primary")
        self.btn_base_start.connect("clicked", lambda b: self.execute_base_ddev_action("start"))
        ctrl_row.pack_start(self.btn_base_start, False, False, 0)
        
        self.btn_base_stop = Gtk.Button(label="⏹ Detener DDEV")
        self.btn_base_stop.connect("clicked", lambda b: self.execute_base_ddev_action("stop"))
        ctrl_row.pack_start(self.btn_base_stop, False, False, 0)
        
        btn_base_composer = Gtk.Button(label="📦 Composer Install")
        btn_base_composer.set_tooltip_text("Instalar o actualizar dependencias de Composer (Drupal Core y Drush)")
        btn_base_composer.connect("clicked", lambda b: self.execute_base_composer_install())
        ctrl_row.pack_start(btn_base_composer, False, False, 0)
        
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
        box.pack_start(header_card, False, False, 0)
        
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
        box.pack_start(self.expander_new, False, False, 0)
        
        # 3. Subsites List Header & ScrolledWindow
        list_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_subsites_count = Gtk.Label()
        self.lbl_subsites_count.set_markup("<b>Subsitios Aprovisionados:</b>")
        self.lbl_subsites_count.set_halign(Gtk.Align.START)
        list_header.pack_start(self.lbl_subsites_count, True, True, 0)
        
        btn_refresh_sub = Gtk.Button(label="🔄 Refrescar")
        btn_refresh_sub.connect("clicked", lambda b: self.refresh_subsites())
        list_header.pack_start(btn_refresh_sub, False, False, 0)
        box.pack_start(list_header, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        self.subsites_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scrolled.add(self.subsites_list_box)
        box.pack_start(scrolled, True, True, 0)
        
        # Bottom close button
        btn_close = Gtk.Button(label="Cerrar")
        btn_close.connect("clicked", lambda b: self.destroy())
        btn_close.set_halign(Gtk.Align.END)
        box.pack_start(btn_close, False, False, 0)
        
        self.show_all()
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
            
        loading_lbl = Gtk.Label(label="Escaneando subsitios de Drupal...")
        self.subsites_list_box.pack_start(loading_lbl, True, True, 10)
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
        
        btn_quick_cr = Gtk.Button(label="⚡ Caché")
        btn_quick_cr.get_style_context().add_class("btn-quick")
        btn_quick_cr.get_style_context().add_class("btn-quick-cache")
        btn_quick_cr.set_tooltip_text(f"Reconstruir caché de {subsite['name']} (drush cr)")
        btn_quick_cr.connect("clicked", lambda b, sn=subsite["name"], su=subsite_url: self.execute_subsite_drush_action("cr", sn, su, base_dir))
        actions_box.pack_start(btn_quick_cr, False, False, 0)
        
        btn_quick_uli = Gtk.Button(label="🔑 Login")
        btn_quick_uli.get_style_context().add_class("btn-quick")
        btn_quick_uli.get_style_context().add_class("btn-quick-login")
        btn_quick_uli.set_tooltip_text(f"Iniciar sesión como Admin en {subsite['name']} (drush uli)")
        btn_quick_uli.connect("clicked", lambda b, sn=subsite["name"], su=subsite_url: self.execute_subsite_drush_action("uli", sn, su, base_dir))
        actions_box.pack_start(btn_quick_uli, False, False, 0)
        
        menu_btn_drush = Gtk.MenuButton()
        menu_btn_drush.set_tooltip_text(f"Herramientas Drush para {subsite['name']}")
        menu_btn_drush.get_style_context().add_class("btn-drupal")
        menu_btn_drush.add(Gtk.Label(label="💧 Drush ▾"))
        
        drush_menu = Gtk.Menu()
        def add_item(menu, label, a_key, s_name, s_url):
            it = Gtk.MenuItem(label=label)
            it.connect("activate", lambda w, ak=a_key, sn=s_name, su=s_url: self.execute_subsite_drush_action(ak, sn, su, base_dir))
            menu.append(it)
            return it
            
        add_item(drush_menu, "🔑 Iniciar Sesión Admin (drush uli)", "uli", subsite["name"], subsite_url)
        add_item(drush_menu, "⚡ Limpiar / Reconstruir Caché (drush cr)", "cr", subsite["name"], subsite_url)
        add_item(drush_menu, "🔄 Actualizar Base de Datos (drush updb)", "updb", subsite["name"], subsite_url)
        drush_menu.append(Gtk.SeparatorMenuItem())
        add_item(drush_menu, "📥 Importar Base de Datos (.sql / .sql.gz)", "import_db", subsite["name"], subsite_url)
        add_item(drush_menu, "📤 Exportar Base de Datos (.sql.gz)", "export_db", subsite["name"], subsite_url)
        drush_menu.append(Gtk.SeparatorMenuItem())
        add_item(drush_menu, "📤 Exportar Configuración (drush cex)", "cex", subsite["name"], subsite_url)
        add_item(drush_menu, "📥 Importar Configuración (drush cim)", "cim", subsite["name"], subsite_url)
        drush_menu.append(Gtk.SeparatorMenuItem())
        add_item(drush_menu, "⏰ Ejecutar Cron (drush cron)", "cron", subsite["name"], subsite_url)
        add_item(drush_menu, "📊 Estado del Subsitio (drush status)", "status", subsite["name"], subsite_url)
        add_item(drush_menu, "📋 Ver Logs Recientes (drush watchdog)", "watchdog", subsite["name"], subsite_url)
        drush_menu.append(Gtk.SeparatorMenuItem())
        add_item(drush_menu, "💻 Abrir SSH en este Subsitio", "ssh", subsite["name"], subsite_url)
        
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
        dialog = ProgressDialog(self, title=f"DDEV: {action.capitalize()} {self.base_name}")
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
        dialog = ProgressDialog(self, title=f"Composer Install: {self.base_name}")
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

        if action_key == "import_db":
            dialog = Gtk.FileChooserDialog(
                title=f"Seleccionar archivo SQL para importar en {subsite_name}",
                parent=self,
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
            
            if dialog.run() == Gtk.ResponseType.OK:
                src_file = dialog.get_filename()
                dialog.destroy()
                
                prog_dialog = ProgressDialog(self, title=f"Importando BD: {subsite_name}")
                prog_dialog.set_status(f"Importando {os.path.basename(src_file)} en base de datos '{subsite_name}'...")
                
                def task():
                    try:
                        GLib.idle_add(prog_dialog.append_log, f"Importando '{src_file}' en base de datos '{subsite_name}'...\n")
                        cmd = ["ddev", "import-db", f"--database={subsite_name}", f"--src={src_file}"]
                        self.run_subproc(cmd, base_dir, prog_dialog)
                        
                        GLib.idle_add(prog_dialog.append_log, f"\nReconstruyendo caché de {subsite_name} (drush cr)...\n")
                        subprocess.run(["ddev", "drush", f"--uri={subsite_url}", "cr"], cwd=base_dir, capture_output=True)
                        
                        GLib.idle_add(prog_dialog.finish, True, f"Base de datos '{subsite_name}' importada con éxito", subsite_url, base_dir)
                    except Exception as ex:
                        GLib.idle_add(prog_dialog.finish, False, f"Error importando BD: {ex}", "", base_dir)
                        
                threading.Thread(target=task, daemon=True).start()
            else:
                dialog.destroy()
            return

        if action_key == "export_db":
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"{subsite_name}_db_{now_str}.sql.gz"
            
            dialog = Gtk.FileChooserDialog(
                title=f"Guardar respaldo de base de datos de {subsite_name}",
                parent=self,
                action=Gtk.FileChooserAction.SAVE
            )
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            dialog.set_current_name(default_filename)
            dialog.set_do_overwrite_confirmation(True)
            
            downloads_dir = os.path.expanduser("~/Descargas")
            if not os.path.exists(downloads_dir):
                downloads_dir = os.path.expanduser("~/Downloads")
            if os.path.exists(downloads_dir):
                dialog.set_current_folder(downloads_dir)
            else:
                dialog.set_current_folder(base_dir)
                
            if dialog.run() == Gtk.ResponseType.OK:
                out_file = dialog.get_filename()
                dialog.destroy()
                
                prog_dialog = ProgressDialog(self, title=f"Exportando BD: {subsite_name}")
                prog_dialog.set_status(f"Exportando base de datos '{subsite_name}' a {os.path.basename(out_file)}...")
                
                def task():
                    try:
                        GLib.idle_add(prog_dialog.append_log, f"Exportando base de datos '{subsite_name}' a '{out_file}'...\n")
                        cmd = ["ddev", "export-db", f"--database={subsite_name}", f"--file={out_file}"]
                        self.run_subproc(cmd, base_dir, prog_dialog)
                        
                        GLib.idle_add(prog_dialog.finish, True, f"Base de datos '{subsite_name}' exportada con éxito", "", os.path.dirname(out_file))
                    except Exception as ex:
                        GLib.idle_add(prog_dialog.finish, False, f"Error exportando BD: {ex}", "", base_dir)
                        
                threading.Thread(target=task, daemon=True).start()
            else:
                dialog.destroy()
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
        
        dialog = ProgressDialog(self, title=f"Drush: {title} ({subsite_name})")
        dialog.set_status(f"Ejecutando en {subsite_name}...")
        
        def task():
            try:
                GLib.idle_add(dialog.append_log, f"$ {cmd_str}\n")
                proc = subprocess.Popen(cmd, cwd=base_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                output_lines = []
                for line in iter(proc.stdout.readline, ''):
                    output_lines.append(line)
                    GLib.idle_add(dialog.append_log, line)
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
            msg = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text="Por favor ingresa un nombre para el subsitio (ej. mikes, corona)")
            msg.run()
            msg.destroy()
            self.entry_subsite_name.grab_focus()
            return

        base_dir = self.base_dir
        if not os.path.exists(base_dir):
            msg = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=f"El proyecto base '{base_dir}' no existe")
            msg.run()
            msg.destroy()
            return

        profile = self.combo_subsite_profile.get_active_id() or "minimal"
        auto_install = self.chk_subsite_auto_install.get_active()
        subsite_domain = f"{slug}.ddev.site"
        subsite_url = f"https://{subsite_domain}"

        dialog = ProgressDialog(self, title=f"Aprovisionando Subsitio: {slug}")
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
            transient_for=self,
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
            del_dialog = ProgressDialog(self, title=f"Eliminando Subsitio {s_name}")
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
        btn_refresh.connect("clicked", lambda b: self.refresh_all())
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

    def refresh_all(self):
        self.refresh_projects()

    def build_main_layout(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)
        
        self.notebook = Gtk.Notebook()
        main_box.pack_start(self.notebook, True, True, 0)
        
        tab_projects = self.build_tab_projects()
        lbl_proj = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_proj.pack_start(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.MENU), False, False, 0)
        self.lbl_proj_title = Gtk.Label(label="Mis Proyectos")
        lbl_proj.pack_start(self.lbl_proj_title, False, False, 0)
        lbl_proj.show_all()
        self.notebook.append_page(tab_projects, lbl_proj)
        
        tab_new = self.build_tab_new_project()
        lbl_new = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_new.pack_start(Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_new.pack_start(Gtk.Label(label="Nuevo Proyecto"), False, False, 0)
        lbl_new.show_all()
        self.notebook.append_page(tab_new, lbl_new)
        
        tab_tools = self.build_tab_tools()
        lbl_tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_tools.pack_start(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_tools.pack_start(Gtk.Label(label="Herramientas"), False, False, 0)
        lbl_tools.show_all()
        self.notebook.append_page(tab_tools, lbl_tools)

    def switch_to_new_project_tab(self, mode="create"):
        self.notebook.set_current_page(1)
        if mode == "import":
            self.btn_mode_import.set_active(True)
        else:
            self.btn_mode_create.set_active(True)

    def on_project_mode_toggled(self, btn):
        if self.btn_mode_import.get_active():
            self.stack_new_project.set_visible_child_name("import")
            self.on_import_path_changed(self.entry_import_path)
        else:
            self.stack_new_project.set_visible_child_name("create")

    def build_tab_new_project(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_vbox.set_margin_start(24)
        main_vbox.set_margin_end(24)
        main_vbox.set_margin_top(16)
        main_vbox.set_margin_bottom(24)
        scrolled.add(main_vbox)
        
        # --- Mode Selector (Segmented buttons) ---
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        mode_box.set_halign(Gtk.Align.CENTER)
        mode_box.set_margin_bottom(6)
        
        self.btn_mode_create = Gtk.RadioButton.new_with_label(None, "📦 Descargar Proyecto Nuevo")
        self.btn_mode_create.set_mode(False)
        self.btn_mode_create.get_style_context().add_class("segmented-btn")
        self.btn_mode_create.connect("toggled", self.on_project_mode_toggled)
        mode_box.pack_start(self.btn_mode_create, False, False, 0)
        
        self.btn_mode_import = Gtk.RadioButton.new_with_label_from_widget(self.btn_mode_create, "📁 Importar Carpeta / Proyecto Existente")
        self.btn_mode_import.set_mode(False)
        self.btn_mode_import.get_style_context().add_class("segmented-btn")
        self.btn_mode_import.connect("toggled", self.on_project_mode_toggled)
        mode_box.pack_start(self.btn_mode_import, False, False, 0)
        
        main_vbox.pack_start(mode_box, False, False, 0)
        
        # --- Stack to switch between Create and Import forms ---
        self.stack_new_project = Gtk.Stack()
        self.stack_new_project.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack_new_project.set_transition_duration(150)
        
        # View 1: Create Form
        self.box_create_view = self.build_create_project_view()
        self.stack_new_project.add_named(self.box_create_view, "create")
        
        # View 2: Import Form
        self.box_import_view = self.build_import_project_view()
        self.stack_new_project.add_named(self.box_import_view, "import")
        
        main_vbox.pack_start(self.stack_new_project, True, True, 0)
        
        self.btn_mode_create.set_active(True)
        return scrolled

    def build_create_project_view(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        
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
        
        # DEDICATED DRUPAL VERSION SELECTOR BOX
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
        
        self.chk_enable_multisite = Gtk.CheckButton(label="Habilitar arquitectura Drupal Multisite (Multi-marca / Multi-dominio)")
        self.chk_enable_multisite.set_tooltip_text("Configura sites.php dinámico y permite crear subsitios independientes (https://<marca>.ddev.site) en este proyecto.")
        self.drupal_version_box.pack_start(self.chk_enable_multisite, False, False, 0)
        
        lbl_ms_desc = Gtk.Label()
        lbl_ms_desc.set_markup("<small><span color='#94a3b8'>Permite gestionar múltiples subsitios compartiendo el mismo núcleo de código con bases de datos y dominios independientes.</span></small>")
        lbl_ms_desc.set_halign(Gtk.Align.START)
        self.drupal_version_box.pack_start(lbl_ms_desc, False, False, 0)
        
        box.pack_start(self.drupal_version_box, False, False, 0)
        
        # Section 3: Advanced Options Expander
        self.expander_new_project = Gtk.Expander(label="Opciones avanzadas (Entorno, Base de datos, etc.)")
        exp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        exp_box.set_margin_top(10)
        exp_box.set_margin_start(16)
        
        grid_adv = Gtk.Grid()
        grid_adv.set_column_spacing(16)
        grid_adv.set_row_spacing(8)
        exp_box.pack_start(grid_adv, False, False, 0)
        
        # Row 0 - PHP Version
        self.lbl_new_php = Gtk.Label(label="Versión de PHP:", halign=Gtk.Align.END)
        self.lbl_new_php.set_no_show_all(True)
        grid_adv.attach(self.lbl_new_php, 0, 0, 1, 1)
        self.combo_php = Gtk.ComboBoxText()
        self.combo_php.set_no_show_all(True)
        for v in ["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]:
            self.combo_php.append_text(v)
        self.combo_php.set_active(0)
        grid_adv.attach(self.combo_php, 1, 0, 1, 1)

        # Row 0 - Node.js Version
        self.lbl_new_nodejs = Gtk.Label(label="Versión de Node.js:", halign=Gtk.Align.END)
        self.lbl_new_nodejs.set_no_show_all(True)
        grid_adv.attach(self.lbl_new_nodejs, 0, 0, 1, 1)
        self.combo_node = Gtk.ComboBoxText()
        self.combo_node.set_no_show_all(True)
        for n in ["22", "20", "18"]:
            self.combo_node.append(n, f"Node.js v{n}")
        self.combo_node.set_active_id("22")
        grid_adv.attach(self.combo_node, 1, 0, 1, 1)

        # Row 0 - Python Runtime Info
        self.lbl_new_python = Gtk.Label(label="Entorno de Ejecución:", halign=Gtk.Align.END)
        self.lbl_new_python.set_no_show_all(True)
        grid_adv.attach(self.lbl_new_python, 0, 0, 1, 1)
        self.lbl_new_python_info = Gtk.Label(halign=Gtk.Align.START)
        self.lbl_new_python_info.set_no_show_all(True)
        self.lbl_new_python_info.set_markup("<span color='#38bdf8'><b>🐍 Python 3.x con entorno virtual .venv aislado</b></span>")
        grid_adv.attach(self.lbl_new_python_info, 1, 0, 1, 1)
        
        # Row 1 - Database
        self.lbl_new_db = Gtk.Label(label="Base de datos:", halign=Gtk.Align.END)
        grid_adv.attach(self.lbl_new_db, 0, 1, 1, 1)
        self.combo_db = Gtk.ComboBoxText()
        grid_adv.attach(self.combo_db, 1, 1, 1, 1)
        
        # Auto install checkbox
        self.chk_auto_install = Gtk.CheckButton(label="Instalar CMS y crear superusuario administrador (admin / admin)")
        self.chk_auto_install.set_no_show_all(True)
        self.chk_auto_install.set_active(True)
        exp_box.pack_start(self.chk_auto_install, False, False, 0)
        
        self.drupal_version_box.set_no_show_all(True)
        self.expander_new_project.add(exp_box)
        box.pack_start(self.expander_new_project, False, False, 0)
        
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
            self.on_framework_selected(self.flowbox_fw, first_child)
            
        return box

    def build_import_project_view(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        
        lbl_info = Gtk.Label()
        lbl_info.set_markup("<b>1. Selecciona la Carpeta de tu Proyecto Existente</b>\n<small><span color='#94a3b8'>Vincula un proyecto o repositorio ya descargado en tu disco para que DDEV Studio lo configure y active.</span></small>")
        lbl_info.set_halign(Gtk.Align.START)
        box.pack_start(lbl_info, False, False, 0)
        
        grid_folder = Gtk.Grid()
        grid_folder.set_column_spacing(16)
        grid_folder.set_row_spacing(10)
        box.pack_start(grid_folder, False, False, 0)
        
        grid_folder.attach(Gtk.Label(label="Carpeta en disco:", halign=Gtk.Align.END), 0, 0, 1, 1)
        
        dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        default_import = "/home/maycol/sites/base-drupal" if os.path.exists("/home/maycol/sites/base-drupal") else DEFAULT_SITES_DIR
        self.entry_import_path = Gtk.Entry()
        self.entry_import_path.set_text(default_import)
        self.entry_import_path.set_hexpand(True)
        self.entry_import_path.connect("changed", self.on_import_path_changed)
        dir_box.pack_start(self.entry_import_path, True, True, 0)
        
        btn_browse = Gtk.Button(label="Examinar...")
        btn_browse.connect("clicked", self.on_browse_import_folder)
        dir_box.pack_start(btn_browse, False, False, 0)
        grid_folder.attach(dir_box, 1, 0, 1, 1)
        
        sec_det = Gtk.Label()
        sec_det.set_markup("<b>2. Detección Automática y Configuración DDEV</b>")
        sec_det.set_halign(Gtk.Align.START)
        sec_det.set_margin_top(8)
        box.pack_start(sec_det, False, False, 0)
        
        self.card_import_details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.card_import_details.get_style_context().add_class("option-highlight-box")
        
        self.lbl_import_status_badge = Gtk.Label()
        self.lbl_import_status_badge.set_halign(Gtk.Align.START)
        self.card_import_details.pack_start(self.lbl_import_status_badge, False, False, 0)
        
        grid_cfg = Gtk.Grid()
        grid_cfg.set_column_spacing(16)
        grid_cfg.set_row_spacing(10)
        self.card_import_details.pack_start(grid_cfg, False, False, 0)
        
        grid_cfg.attach(Gtk.Label(label="Nombre en DDEV:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.entry_import_name = Gtk.Entry()
        self.entry_import_name.set_hexpand(True)
        grid_cfg.attach(self.entry_import_name, 1, 0, 1, 1)
        
        grid_cfg.attach(Gtk.Label(label="Tecnología detectada:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.combo_import_type = Gtk.ComboBoxText()
        for t_id, t_lbl in [
            ("drupal11", "Drupal 11"),
            ("drupal10", "Drupal 10"),
            ("drupal9", "Drupal 9"),
            ("drupal8", "Drupal 8"),
            ("drupal7", "Drupal 7"),
            ("wordpress", "WordPress"),
            ("laravel", "Laravel"),
            ("symfony", "Symfony"),
            ("django", "Django (Python)"),
            ("flask", "Flask (Python)"),
            ("angular", "Angular (Node.js)"),
            ("react", "React (Node.js)"),
            ("vue", "Vue (Node.js)"),
            ("php", "PHP Estándar"),
            ("generic", "Generic / Node.js")
        ]:
            self.combo_import_type.append(t_id, t_lbl)
        self.combo_import_type.set_active_id("drupal10")
        self.combo_import_type.connect("changed", self.on_import_type_changed)
        grid_cfg.attach(self.combo_import_type, 1, 1, 1, 1)
        
        grid_cfg.attach(Gtk.Label(label="Directorio Web (Docroot):", halign=Gtk.Align.END), 0, 2, 1, 1)
        self.combo_import_docroot = Gtk.ComboBoxText()
        for dr in ["docroot", "web", "public", "dist", "."]:
            self.combo_import_docroot.append_text(dr)
        self.combo_import_docroot.set_active(0)
        grid_cfg.attach(self.combo_import_docroot, 1, 2, 1, 1)
        
        # Row 3 - PHP Runtime
        self.lbl_import_php = Gtk.Label(label="Versión de PHP:", halign=Gtk.Align.END)
        self.lbl_import_php.set_no_show_all(True)
        grid_cfg.attach(self.lbl_import_php, 0, 3, 1, 1)
        self.combo_import_php = Gtk.ComboBoxText()
        self.combo_import_php.set_no_show_all(True)
        for v in ["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]:
            self.combo_import_php.append_text(v)
        self.combo_import_php.set_active(0)
        grid_cfg.attach(self.combo_import_php, 1, 3, 1, 1)

        # Row 3 - Node.js Runtime
        self.lbl_import_nodejs = Gtk.Label(label="Versión de Node.js:", halign=Gtk.Align.END)
        self.lbl_import_nodejs.set_no_show_all(True)
        grid_cfg.attach(self.lbl_import_nodejs, 0, 3, 1, 1)
        self.combo_import_nodejs = Gtk.ComboBoxText()
        self.combo_import_nodejs.set_no_show_all(True)
        for nv in ["22", "20", "18"]:
            self.combo_import_nodejs.append(nv, f"Node.js v{nv}")
        self.combo_import_nodejs.set_active_id("22")
        grid_cfg.attach(self.combo_import_nodejs, 1, 3, 1, 1)

        # Row 3 - Python Runtime
        self.lbl_import_python = Gtk.Label(label="Entorno de Ejecución:", halign=Gtk.Align.END)
        self.lbl_import_python.set_no_show_all(True)
        grid_cfg.attach(self.lbl_import_python, 0, 3, 1, 1)
        self.lbl_import_python_info = Gtk.Label(halign=Gtk.Align.START)
        self.lbl_import_python_info.set_no_show_all(True)
        self.lbl_import_python_info.set_markup("<span color='#38bdf8'><b>🐍 Python 3.x con entorno .venv aislado</b></span>")
        grid_cfg.attach(self.lbl_import_python_info, 1, 3, 1, 1)
        
        # Row 4 - Database
        grid_cfg.attach(Gtk.Label(label="Base de Datos:", halign=Gtk.Align.END), 0, 4, 1, 1)
        self.combo_import_db = Gtk.ComboBoxText()
        grid_cfg.attach(self.combo_import_db, 1, 4, 1, 1)
        
        # Options box
        self.box_import_drupal_options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.box_import_drupal_options.set_no_show_all(True)
        self.chk_import_multisite = Gtk.CheckButton(label="Habilitar arquitectura Drupal Multisite (Configurar sites.php dinámico)")
        self.chk_import_multisite.set_active(True)
        self.box_import_drupal_options.pack_start(self.chk_import_multisite, False, False, 0)
        
        lbl_ms_hint = Gtk.Label()
        lbl_ms_hint.set_markup("<small><span color='#94a3b8'>Permite crear múltiples marcas y subsitios con bases de datos y dominios independientes en este proyecto.</span></small>")
        lbl_ms_hint.set_halign(Gtk.Align.START)
        self.box_import_drupal_options.pack_start(lbl_ms_hint, False, False, 0)
        self.card_import_details.pack_start(self.box_import_drupal_options, False, False, 0)
        
        self.chk_import_composer = Gtk.CheckButton(label="Ejecutar 'ddev composer install' si faltan dependencias o Drush")
        self.chk_import_composer.set_active(True)
        self.card_import_details.pack_start(self.chk_import_composer, False, False, 0)
        
        box.pack_start(self.card_import_details, False, False, 0)
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_margin_top(12)
        btn_box.set_halign(Gtk.Align.END)
        
        self.btn_import_submit = Gtk.Button(label="🚀 Importar y Activar Proyecto en DDEV")
        self.btn_import_submit.get_style_context().add_class("btn-primary")
        self.btn_import_submit.connect("clicked", self.on_import_project_clicked)
        btn_box.pack_start(self.btn_import_submit, False, False, 0)
        box.pack_start(btn_box, False, False, 0)
        
        return box

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
            
            is_drupal = (fw_id == "drupal")
            is_php = fw_id in ["drupal", "wordpress", "laravel", "symfony", "php"]
            is_node = fw_id in ["angular", "react", "vue", "generic"]
            is_python = fw_id in ["django", "flask"]
            
            # Show/hide Drupal version selector
            if is_drupal:
                self.drupal_version_box.show_all()
                self.on_drupal_version_changed(self.combo_drupal_ver)
            else:
                self.drupal_version_box.hide()
                php_val = self.selected_framework.get("php", "8.3")
                for idx, text in enumerate(["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]):
                    if text == php_val:
                        self.combo_php.set_active(idx)
                        break

            # Runtime fields visibility in Advanced Options
            if hasattr(self, "lbl_new_php") and hasattr(self, "combo_php"):
                if is_php:
                    self.lbl_new_php.show()
                    self.combo_php.show()
                else:
                    self.lbl_new_php.hide()
                    self.combo_php.hide()
                    
            if hasattr(self, "lbl_new_nodejs") and hasattr(self, "combo_node"):
                if is_node:
                    self.lbl_new_nodejs.show()
                    self.combo_node.show()
                else:
                    self.lbl_new_nodejs.hide()
                    self.combo_node.hide()
                    
            if hasattr(self, "lbl_new_python") and hasattr(self, "lbl_new_python_info"):
                if is_python:
                    self.lbl_new_python.show()
                    self.lbl_new_python_info.show()
                else:
                    self.lbl_new_python.hide()
                    self.lbl_new_python_info.hide()

            # Database options in Advanced Options
            if hasattr(self, "combo_db"):
                curr_db = self.combo_db.get_active_id()
                self.combo_db.remove_all()
                if is_node:
                    self.combo_db.append("none", "🚫 Ninguna (Solo Frontend / Ahorro de RAM)")
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.append("postgres:16", "PostgreSQL 16")
                    self.combo_db.set_active_id("none")
                elif fw_id == "django":
                    self.combo_db.append("postgres:16", "PostgreSQL 16 (Recomendada)")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11")
                    self.combo_db.set_active_id("postgres:16")
                elif fw_id == "flask":
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11 (Recomendada)")
                    self.combo_db.append("postgres:16", "PostgreSQL 16")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.set_active_id("mariadb:10.11")
                else:
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11 (Recomendada)")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.append("postgres:16", "PostgreSQL 16")
                    self.combo_db.append("mariadb:10.5", "MariaDB 10.5")
                    self.combo_db.set_active_id("mariadb:10.11")

            # Checkbox auto-install contextual
            if hasattr(self, "chk_auto_install"):
                if fw_id == "drupal":
                    self.chk_auto_install.set_label("Instalar Drupal y crear superusuario administrador (admin / admin)")
                    self.chk_auto_install.show()
                    self.chk_auto_install.set_active(True)
                elif fw_id == "wordpress":
                    self.chk_auto_install.set_label("Instalar WordPress y crear usuario administrador (admin / admin)")
                    self.chk_auto_install.show()
                    self.chk_auto_install.set_active(True)
                elif fw_id == "django":
                    self.chk_auto_install.set_label("Crear superusuario (admin / admin) y ejecutar migraciones iniciales")
                    self.chk_auto_install.show()
                    self.chk_auto_install.set_active(True)
                else:
                    self.chk_auto_install.hide()

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
        
        btn_import_shortcut = Gtk.Button(label="📁 Importar Carpeta...")
        btn_import_shortcut.set_tooltip_text("Vincular un proyecto o repositorio existente en tu disco a DDEV")
        btn_import_shortcut.connect("clicked", lambda b: self.switch_to_new_project_tab("import"))
        search_box.pack_start(btn_import_shortcut, False, False, 0)
        
        btn_new_shortcut = Gtk.Button(label="➕ Nuevo...")
        btn_new_shortcut.set_tooltip_text("Crear un nuevo proyecto desde cero")
        btn_new_shortcut.connect("clicked", lambda b: self.switch_to_new_project_tab("create"))
        search_box.pack_start(btn_new_shortcut, False, False, 0)
        
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
            lbl_empty.set_markup("<b>No hay proyectos de DDEV activos</b>\nCrea uno nuevo desde cero o importa una carpeta que ya tengas en tu disco.")
            lbl_empty.set_justify(Gtk.Justification.CENTER)
            empty_box.pack_start(lbl_empty, False, False, 0)
            
            btn_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            btn_actions_box.set_halign(Gtk.Align.CENTER)
            btn_actions_box.set_margin_top(10)
            
            btn_create = Gtk.Button(label="➕ Crear Proyecto Nuevo")
            btn_create.get_style_context().add_class("btn-primary")
            btn_create.connect("clicked", lambda b: self.switch_to_new_project_tab("create"))
            btn_actions_box.pack_start(btn_create, False, False, 0)
            
            btn_import = Gtk.Button(label="📁 Importar Carpeta Existente")
            btn_import.connect("clicked", lambda b: self.switch_to_new_project_tab("import"))
            btn_actions_box.pack_start(btn_import, False, False, 0)
            
            empty_box.pack_start(btn_actions_box, False, False, 0)
            
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
        approot = proj.get("approot", "")
        icon_name = "php.svg"
        if "wordpress" in ptype:
            icon_name = "wordpress.svg"
        elif "drupal" in ptype:
            icon_name = "drupal.svg"
        elif "laravel" in ptype:
            icon_name = "laravel.svg"
        elif "django" in ptype or (approot and os.path.exists(os.path.join(approot, "manage.py"))):
            icon_name = "django.svg"
        elif "flask" in ptype or (approot and (os.path.exists(os.path.join(approot, "app.py")) or os.path.exists(os.path.join(approot, "wsgi.py")))):
            icon_name = "flask.svg"
        elif "angular" in ptype or (approot and os.path.exists(os.path.join(approot, "angular.json"))):
            icon_name = "angular.svg"
        elif "react" in ptype:
            icon_name = "react.svg"
        elif "vue" in ptype:
            icon_name = "vue.svg"
        elif "symfony" in ptype:
            icon_name = "symfony.svg"
        elif "generic" in ptype or "vite" in ptype:
            icon_name = "react.svg"
            
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
        
        approot = proj.get("approot", "")
        is_drupal = "drupal" in ptype or (approot and (os.path.exists(os.path.join(approot, "docroot", "sites")) or os.path.exists(os.path.join(approot, "web", "sites")) or os.path.exists(os.path.join(approot, "sites"))))
        if is_drupal:
            subsite_count = 0
            
            # Scan sites directory for actual subsite folders
            for d in ["docroot", "web", "."]:
                sites_dir = os.path.join(approot, d, "sites") if approot else ""
                if sites_dir and os.path.isdir(sites_dir):
                    try:
                        entries = [
                            e for e in os.listdir(sites_dir)
                            if os.path.isdir(os.path.join(sites_dir, e)) and e not in ['default', 'all', 'g', 'settings', 'simpletest']
                        ]
                        if entries:
                            subsite_count = len(entries)
                            break
                    except Exception:
                        pass
                        
            is_multisite = (subsite_count > 0)
            
            lbl_drupal_mode = Gtk.Label()
            lbl_drupal_mode.get_style_context().add_class("badge")
            if is_multisite:
                lbl_drupal_mode.set_label(f"💧 MULTISITE ({subsite_count})")
                lbl_drupal_mode.get_style_context().add_class("badge-multisite")
                lbl_drupal_mode.set_tooltip_text(f"Drupal Multisite con {subsite_count} subsitio(s) configurado(s)")
            else:
                lbl_drupal_mode.set_label("💧 SITE")
                lbl_drupal_mode.get_style_context().add_class("badge-single-site")
                lbl_drupal_mode.set_tooltip_text("Drupal Single Site (Sitio estándar individual)")
            title_row.pack_start(lbl_drupal_mode, False, False, 0)
        
        info_box.pack_start(title_row, False, False, 0)
        
        primary_url = proj.get("primary_url") or proj.get("httpsurl") or proj.get("httpurl") or ""
        lbl_url = Gtk.Label()
        if primary_url:
            lbl_url.set_markup(f"🌐 <a href='{primary_url}'><b>{primary_url}</b></a>")
        else:
            lbl_url.set_markup("<span color='#9ca3af'>🌐 Sin URL activa</span>")
        lbl_url.set_halign(Gtk.Align.START)
        info_box.pack_start(lbl_url, False, False, 0)
        
        lbl_path = Gtk.Label()
        if approot:
            lbl_path.set_markup(f"<small><span color='#94a3b8'>📁 <b>Ubicación:</b> {approot}</span></small>")
        else:
            lbl_path.set_markup("<small><span color='#94a3b8'>📁 <i>Ubicación no disponible</i></span></small>")
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
            
        # Controles y herramientas especializadas de Drupal
        if is_drupal:
            btn_subsites = Gtk.Button()
            btn_subsites.get_style_context().add_class("btn-drupal")
            if is_multisite and subsite_count > 0:
                btn_subsites.set_label(f"💧 Subsitios ({subsite_count})")
                btn_subsites.set_tooltip_text(f"Gestionar los {subsite_count} subsitios de este Drupal Multisite")
            else:
                btn_subsites.set_label("💧 Subsitios")
                btn_subsites.set_tooltip_text("Gestionar o aprovisionar subsitios multisite para este proyecto")
            btn_subsites.connect("clicked", lambda b, p=proj: self.open_subsites_manager(p))
            actions_box.pack_start(btn_subsites, False, False, 0)
            
            # 1. Botón rápido Reconstruir/Limpiar Caché (cr / cc all)
            btn_quick_cr = Gtk.Button(label="⚡ Caché")
            btn_quick_cr.get_style_context().add_class("btn-quick")
            btn_quick_cr.get_style_context().add_class("btn-quick-cache")
            btn_quick_cr.set_tooltip_text("Reconstruir caché de Drupal (ddev drush cr)")
            btn_quick_cr.connect("clicked", lambda b, p=proj: self.execute_drush_action("cr", p))
            actions_box.pack_start(btn_quick_cr, False, False, 0)
            
            # 2. Botón rápido One-Time Login (drush uli)
            btn_quick_uli = Gtk.Button(label="🔑 Login")
            btn_quick_uli.get_style_context().add_class("btn-quick")
            btn_quick_uli.get_style_context().add_class("btn-quick-login")
            btn_quick_uli.set_tooltip_text("Iniciar sesión como Administrador (ddev drush uli)")
            btn_quick_uli.connect("clicked", lambda b, p=proj: self.execute_drush_action("uli", p))
            actions_box.pack_start(btn_quick_uli, False, False, 0)
            
            # 3. Menú desplegable completo de herramientas Drush
            menu_btn_drush = Gtk.MenuButton()
            menu_btn_drush.set_tooltip_text("Menú de comandos de Drupal / Drush")
            menu_btn_drush.get_style_context().add_class("btn-drupal")
            
            lbl_drush_menu = Gtk.Label(label="💧 Drush ▾")
            menu_btn_drush.add(lbl_drush_menu)
            
            drush_menu = Gtk.Menu()
            
            def add_menu_item(menu, label, action_key, p):
                item = Gtk.MenuItem(label=label)
                item.connect("activate", lambda w, ak=action_key, pr=p: self.execute_drush_action(ak, pr))
                menu.append(item)
                return item
                
            add_menu_item(drush_menu, "🔑 Iniciar Sesión Admin (drush uli)", "uli", proj)
            add_menu_item(drush_menu, "⚡ Limpiar / Reconstruir Caché (drush cr)", "cr", proj)
            add_menu_item(drush_menu, "🔄 Actualizar Base de Datos (drush updb)", "updb", proj)
            
            drush_menu.append(Gtk.SeparatorMenuItem())
            add_menu_item(drush_menu, "📥 Importar Base de Datos (.sql / .sql.gz)", "import_db", proj)
            add_menu_item(drush_menu, "📤 Exportar Base de Datos (.sql.gz)", "export_db", proj)
            drush_menu.append(Gtk.SeparatorMenuItem())
            
            if "drupal7" not in ptype:
                add_menu_item(drush_menu, "📤 Exportar Configuración (drush cex)", "cex", proj)
                add_menu_item(drush_menu, "📥 Importar Configuración (drush cim)", "cim", proj)
                drush_menu.append(Gtk.SeparatorMenuItem())
                
            add_menu_item(drush_menu, "⏰ Ejecutar Cron (drush cron)", "cron", proj)
            add_menu_item(drush_menu, "📊 Estado del Sitio (drush status)", "status", proj)
            add_menu_item(drush_menu, "📋 Ver Logs Recientes (drush watchdog)", "watchdog", proj)
            add_menu_item(drush_menu, "🧩 Módulos Habilitados (drush pm:list)", "pm_list", proj)
            
            drush_menu.append(Gtk.SeparatorMenuItem())
            add_menu_item(drush_menu, "💻 Abrir SSH en Contenedor (ddev ssh)", "ssh", proj)
            add_menu_item(drush_menu, "🚀 Instalar Drush si falta (composer require)", "install_drush", proj)
            
            drush_menu.show_all()
            menu_btn_drush.set_popup(drush_menu)
            actions_box.pack_start(menu_btn_drush, False, False, 0)

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

    def open_terminal(self, path, command=""):
        for term in ["mate-terminal", "gnome-terminal", "x-terminal-emulator", "xterm"]:
            if shutil.which(term):
                if term in ["mate-terminal", "gnome-terminal"]:
                    if command:
                        subprocess.Popen([term, f"--working-directory={path}", "-e", f"bash -c '{command}; exec bash'"])
                    else:
                        subprocess.Popen([term, f"--working-directory={path}"])
                else:
                    if command:
                        subprocess.Popen([term, "-e", f"bash -c '{command}; exec bash'"], cwd=path)
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

    def execute_drush_action(self, action_key, proj):
        approot = proj.get("approot", "")
        pname = proj.get("name", "")
        ptype = proj.get("type", "").lower()
        primary_url = proj.get("primary_url") or proj.get("httpsurl") or proj.get("httpurl") or ""
        status = proj.get("status", "").lower()
        is_running = "running" in status or "ok" in status
        is_drupal7 = "drupal7" in ptype
        
        drush_configs = {
            "cr": {
                "title": "Limpiar Caché",
                "cmd": ["ddev", "drush", "cc", "all"] if is_drupal7 else ["ddev", "drush", "cr"],
                "desc": "ddev drush cc all" if is_drupal7 else "ddev drush cr",
                "success_msg": "Caché de Drupal reconstruida correctamente"
            },
            "uli": {
                "title": "Login Administrador",
                "cmd": ["ddev", "drush", "uli"],
                "desc": "ddev drush uli",
                "success_msg": "Enlace de inicio de sesión generado con éxito"
            },
            "updb": {
                "title": "Actualizar Base de Datos",
                "cmd": ["ddev", "drush", "updatedb", "-y"],
                "desc": "ddev drush updatedb -y",
                "success_msg": "Actualizaciones de base de datos completadas con éxito"
            },
            "cex": {
                "title": "Exportar Configuración",
                "cmd": ["ddev", "drush", "config:export", "-y"],
                "desc": "ddev drush config:export -y",
                "success_msg": "Configuración activa exportada a directorio de sincronización"
            },
            "cim": {
                "title": "Importar Configuración",
                "cmd": ["ddev", "drush", "config:import", "-y"],
                "desc": "ddev drush config:import -y",
                "success_msg": "Configuración importada exitosamente"
            },
            "cron": {
                "title": "Ejecutar Cron",
                "cmd": ["ddev", "drush", "cron"],
                "desc": "ddev drush cron",
                "success_msg": "Cron de Drupal ejecutado con éxito"
            },
            "status": {
                "title": "Estado de Drupal",
                "cmd": ["ddev", "drush", "status"],
                "desc": "ddev drush status",
                "success_msg": "Estado de Drupal consultado exitosamente"
            },
            "watchdog": {
                "title": "Logs Recientes (Watchdog)",
                "cmd": ["ddev", "drush", "watchdog:show", "--count=30"],
                "desc": "ddev drush watchdog:show --count=30",
                "success_msg": "Logs recientes obtenidos exitosamente"
            },
            "pm_list": {
                "title": "Módulos Habilitados",
                "cmd": ["ddev", "drush", "pm:list", "--status=enabled"],
                "desc": "ddev drush pm:list --status=enabled",
                "success_msg": "Lista de módulos obtenida exitosamente"
            },
            "install_drush": {
                "title": "Instalar Drush",
                "cmd": ["ddev", "composer", "require", "drush/drush:^10" if "drupal8" in ptype else "drush/drush"],
                "desc": "ddev composer require drush/drush",
                "success_msg": "Drush instalado en el proyecto"
            }
        }
        
        if action_key == "ssh":
            self.open_terminal(approot, "ddev ssh")
            return

        if action_key == "import_db":
            self.on_import_db(None, proj)
            return

        if action_key == "export_db":
            self.on_export_db(None, proj)
            return
            
        cfg = drush_configs.get(action_key)
        if not cfg:
            return
            
        cmd = cfg["cmd"]
        cmd_desc = cfg["desc"]
        action_title = cfg["title"]
        success_default_msg = cfg["success_msg"]

        if not is_running:
            confirm = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=f"El proyecto '{pname}' está detenido."
            )
            confirm.format_secondary_text(
                f"Para ejecutar '{cmd_desc}', es necesario iniciar el entorno DDEV.\n\n¿Deseas iniciar el proyecto ahora y ejecutar la acción?"
            )
            res = confirm.run()
            confirm.destroy()
            if res != Gtk.ResponseType.OK:
                return

        dialog = ProgressDialog(self, title=f"Drush: {action_title} ({pname})")
        dialog.set_status(f"Ejecutando {cmd_desc} en {pname}...")

        def task():
            try:
                if not is_running:
                    GLib.idle_add(dialog.append_log, f"Iniciando proyecto '{pname}'...\n$ ddev start -y\n")
                    p_start = subprocess.run(["ddev", "start", "-y"], cwd=approot, capture_output=True, text=True)
                    GLib.idle_add(dialog.append_log, p_start.stdout + p_start.stderr + "\n")
                    if p_start.returncode != 0:
                        GLib.idle_add(dialog.finish, False, "No se pudo iniciar el proyecto DDEV", "", approot)
                        return

                GLib.idle_add(dialog.append_log, f"$ {' '.join(cmd)}\n")
                process = subprocess.Popen(
                    cmd,
                    cwd=approot,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                output_lines = []
                for line in iter(process.stdout.readline, ''):
                    if line:
                        output_lines.append(line)
                        GLib.idle_add(dialog.append_log, line)
                process.stdout.close()
                process.wait()
                
                success = (process.returncode == 0)
                full_output = "".join(output_lines)
                
                detected_url = ""
                if action_key == "uli" and success:
                    # Limpiar caracteres ANSI si existen
                    clean_output = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', full_output)
                    match = re.search(r'(https?://[^\s]+(?:/user/reset/[^\s]+|/login[^\s]*))', clean_output)
                    if not match:
                        match = re.search(r'(https?://[^\s]+)', clean_output)
                    if match:
                        raw_url = match.group(1).strip().rstrip('.,;)')
                        if primary_url:
                            parsed_primary = primary_url.rstrip('/')
                            fixed_url = re.sub(r'^https?://(default|127\.0\.0\.1|localhost)(:\d+)?', parsed_primary, raw_url)
                        else:
                            fixed_url = raw_url
                        detected_url = fixed_url
                        # Abrir la URL exactamente 1 sola vez en el navegador
                        try:
                            webbrowser.open(detected_url)
                        except Exception:
                            pass
                
                if success:
                    msg = success_default_msg
                else:
                    if "drush is not available" in full_output or "drush: command not found" in full_output:
                        msg = "Drush no está instalado en el proyecto. Usa la opción 'Instalar Drush'."
                    else:
                        msg = f"Error al ejecutar {action_title} ({cmd_desc})"
                
                finish_url = detected_url or (primary_url if not is_running else "")
                GLib.idle_add(dialog.finish, success, msg, finish_url, approot)
                GLib.idle_add(self.refresh_projects)
            except Exception as ex:
                GLib.idle_add(dialog.append_log, f"\nExcepción: {str(ex)}\n")
                GLib.idle_add(dialog.finish, False, f"Error: {str(ex)}", "", approot)

        threading.Thread(target=task, daemon=True).start()

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

    def open_subsites_manager(self, proj):
        dlg = SubsitesManagerDialog(self, proj, self)
        dlg.run()

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

    def on_browse_import_folder(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar carpeta de proyecto existente",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        curr = self.entry_import_path.get_text().strip()
        if os.path.exists(curr):
            dialog.set_current_folder(curr)
        if dialog.run() == Gtk.ResponseType.OK:
            self.entry_import_path.set_text(dialog.get_filename())
            self.on_import_path_changed(self.entry_import_path)
        dialog.destroy()

    def on_import_path_changed(self, entry):
        p = entry.get_text().strip()
        if not hasattr(self, "card_import_details"):
            return
            
        det = detect_project_details(p)
        if not det["valid"]:
            self.lbl_import_status_badge.set_markup("<span color='#ef4444'><b>✗ Carpeta no encontrada o inaccesible</b></span>")
            self.btn_import_submit.set_sensitive(False)
            return
            
        self.btn_import_submit.set_sensitive(True)
        self.lbl_import_status_badge.set_markup(f"<span color='#10b981'><b>✓ {det['summary']}</b></span>")
        self.entry_import_name.set_text(det["name"])
        
        # Set type combo
        self.combo_import_type.set_active_id(det["type"])
        
        # Set docroot combo
        for idx, text in enumerate(["docroot", "web", "public", "dist", "."]):
            if text == det["docroot"]:
                self.combo_import_docroot.set_active(idx)
                break
                
        # Set php combo
        for idx, text in enumerate(["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]):
            if text == det.get("php", "8.3"):
                self.combo_import_php.set_active(idx)
                break
                
        # Set nodejs combo
        if hasattr(self, "combo_import_nodejs") and det.get("nodejs"):
            self.combo_import_nodejs.set_active_id(det["nodejs"])
            
        self.on_import_type_changed(self.combo_import_type)
        
        # Set db combo after on_import_type_changed populated it
        if hasattr(self, "combo_import_db") and det.get("db"):
            self.combo_import_db.set_active_id(det["db"])

    def on_import_type_changed(self, combo):
        t_id = combo.get_active_id() or ""
        is_dr = "drupal" in t_id
        is_php = is_dr or t_id in ["laravel", "php", "symfony", "wordpress"]
        is_node = t_id in ["angular", "react", "vue", "generic"]
        is_python = t_id in ["django", "flask"]
        
        if hasattr(self, "box_import_drupal_options"):
            if is_dr:
                self.box_import_drupal_options.show_all()
            else:
                self.box_import_drupal_options.hide()
            
        # Runtime visibility
        if hasattr(self, "lbl_import_php") and hasattr(self, "combo_import_php"):
            if is_php:
                self.lbl_import_php.show()
                self.combo_import_php.show()
            else:
                self.lbl_import_php.hide()
                self.combo_import_php.hide()
                
        if hasattr(self, "lbl_import_nodejs") and hasattr(self, "combo_import_nodejs"):
            if is_node:
                self.lbl_import_nodejs.show()
                self.combo_import_nodejs.show()
            else:
                self.lbl_import_nodejs.hide()
                self.combo_import_nodejs.hide()
                
        if hasattr(self, "lbl_import_python") and hasattr(self, "lbl_import_python_info"):
            if is_python:
                self.lbl_import_python.show()
                self.lbl_import_python_info.show()
            else:
                self.lbl_import_python.hide()
                self.lbl_import_python_info.hide()
            
        # Database options
        if hasattr(self, "combo_import_db"):
            curr_db = self.combo_import_db.get_active_id()
            self.combo_import_db.remove_all()
            if is_node:
                self.combo_import_db.append("none", "🚫 Ninguna (Solo Frontend / Ahorro de RAM)")
                self.combo_import_db.append("mariadb:10.11", "MariaDB 10.11")
                self.combo_import_db.append("mysql:8.0", "MySQL 8.0")
                self.combo_import_db.append("postgres:16", "PostgreSQL 16")
                if curr_db in ["mariadb:10.11", "mysql:8.0", "postgres:16"]:
                    self.combo_import_db.set_active_id(curr_db)
                else:
                    self.combo_import_db.set_active_id("none")
            elif is_python:
                self.combo_import_db.append("postgres:16", "PostgreSQL 16 (Recomendada)")
                self.combo_import_db.append("mysql:8.0", "MySQL 8.0")
                self.combo_import_db.append("mariadb:10.11", "MariaDB 10.11")
                if curr_db in ["mysql:8.0", "mariadb:10.11"]:
                    self.combo_import_db.set_active_id(curr_db)
                else:
                    self.combo_import_db.set_active_id("postgres:16")
            else:
                self.combo_import_db.append("mariadb:10.11", "MariaDB 10.11 (Recomendada)")
                self.combo_import_db.append("mysql:8.0", "MySQL 8.0")
                self.combo_import_db.append("postgres:16", "PostgreSQL 16")
                self.combo_import_db.append("mariadb:10.5", "MariaDB 10.5")
                if curr_db in ["mysql:8.0", "postgres:16", "mariadb:10.5"]:
                    self.combo_import_db.set_active_id(curr_db)
                else:
                    self.combo_import_db.set_active_id("mariadb:10.11")
                    
        # Checkbox label
        if hasattr(self, "chk_import_composer"):
            if is_dr:
                self.chk_import_composer.set_label("Ejecutar 'ddev composer install' si falta vendor/ (Drush y dependencias de Drupal)")
            elif t_id == "wordpress":
                self.chk_import_composer.set_label("Ejecutar 'ddev composer install' si el proyecto usa Composer (Bedrock)")
            elif is_php:
                self.chk_import_composer.set_label("Ejecutar 'ddev composer install' si falta la carpeta vendor/")
            elif is_node:
                self.chk_import_composer.set_label("Ejecutar 'ddev npm install' si falta la carpeta node_modules/")
            elif is_python:
                self.chk_import_composer.set_label("Instalar dependencias de Python si falta el entorno .venv/")
            else:
                self.chk_import_composer.set_label("Instalar dependencias automáticamente si faltan")

    def on_import_project_clicked(self, widget):
        target_dir = self.entry_import_path.get_text().strip()
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            msg_diag = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="La carpeta seleccionada no existe o no es válida."
            )
            msg_diag.run()
            msg_diag.destroy()
            return
            
        raw_name = self.entry_import_name.get_text().strip()
        slug = re.sub(r'[^a-zA-Z0-9_-]', '-', raw_name).lower()
        if not slug:
            slug = os.path.basename(target_dir.rstrip("/"))
            
        p_type = self.combo_import_type.get_active_id() or "drupal10"
        docroot = self.combo_import_docroot.get_active_text() or "docroot"
        php_ver = self.combo_import_php.get_active_text() or "8.3"
        node_ver = self.combo_import_nodejs.get_active_id() if hasattr(self, "combo_import_nodejs") else "22"
        db_type = self.combo_import_db.get_active_id() or "mariadb:10.11"
        is_multisite = ("drupal" in p_type) and self.chk_import_multisite.get_active()
        do_composer = self.chk_import_composer.get_active()
        
        is_php = ("drupal" in p_type) or p_type in ["laravel", "php", "symfony", "wordpress"]
        is_node = p_type in ["angular", "react", "vue", "generic"]
        is_python = p_type in ["django", "flask"]
        
        dialog = ProgressDialog(self, title=f"Importando Proyecto: {slug}")
        dialog.set_status(f"Configurando DDEV en {target_dir}...")
        
        def run_import():
            try:
                def log(text):
                    GLib.idle_add(dialog.append_log, text + "\n")
                def set_st(st):
                    GLib.idle_add(dialog.set_status, st)
                    
                log(f"📁 Directorio base: {target_dir}")
                log(f"🚀 Tecnología: {p_type} | Docroot: {docroot}")
                if is_php:
                    log(f"🐘 PHP: {php_ver} | BD: {db_type}")
                elif is_node:
                    log(f"🟢 Node.js: v{node_ver} | BD: {db_type}")
                elif is_python:
                    log(f"🐍 Python 3 + venv | BD: {db_type}")
                log("="*50)
                
                # 1. ddev config
                set_st("Configurando DDEV en el proyecto...")
                ddev_type = p_type
                if p_type in ["angular", "react", "vue", "django", "flask"]:
                    ddev_type = "generic"
                elif p_type == "symfony":
                    ddev_type = "php"
                    
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    f"--project-type={ddev_type}",
                    f"--docroot={docroot}"
                ]
                
                if is_php:
                    cfg_cmd.append(f"--php-version={php_ver}")
                elif is_node:
                    cfg_cmd.append(f"--nodejs-version={node_ver}")
                    if p_type == "angular":
                        cfg_cmd.append("--web-environment-add=NG_CLI_ANALYTICS=false")
                elif is_python:
                    cfg_cmd.append("--webimage-extra-packages=python3-venv,python3-pip")
                    
                if db_type == "none":
                    cfg_cmd.append("--omit-containers=db")
                else:
                    cfg_cmd.append(f"--database={db_type}")
                    
                self.run_subproc(cfg_cmd, target_dir, dialog)
                
                # Daemon & Reverse Proxy for non-PHP stacks if needed
                if p_type == "django":
                    os.makedirs(os.path.join(target_dir, ".ddev", "nginx_full"), exist_ok=True)
                    with open(os.path.join(target_dir, ".ddev", "nginx_full", "nginx-site.conf"), "w") as nf:
                        nf.write("""location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
""")
                    with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                        df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: django-server
    command: "/var/www/html/.venv/bin/python manage.py runserver 0.0.0.0:8000"
    directory: /var/www/html
""")
                elif p_type == "flask":
                    os.makedirs(os.path.join(target_dir, ".ddev", "nginx_full"), exist_ok=True)
                    with open(os.path.join(target_dir, ".ddev", "nginx_full", "nginx-site.conf"), "w") as nf:
                        nf.write("""location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
""")
                    with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                        df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: flask-server
    command: "/var/www/html/.venv/bin/python app.py"
    directory: /var/www/html
""")
                elif p_type == "angular":
                    os.makedirs(os.path.join(target_dir, ".ddev", "nginx_full"), exist_ok=True)
                    with open(os.path.join(target_dir, ".ddev", "nginx_full", "nginx-site.conf"), "w") as nf:
                        nf.write("""location / {
    proxy_pass http://127.0.0.1:4200;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
""")
                    with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                        df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: angular-dev-server
    command: "npx ng serve --host 0.0.0.0 --port 4200 --allowed-hosts"
    directory: /var/www/html
""")
                
                # 2. Dynamic sites.php if Drupal Multisite
                if is_multisite:
                    set_st("Configurando enrutador dinámico Drupal Multisite...")
                    sites_dir = os.path.join(target_dir, docroot, "sites") if docroot != "." else os.path.join(target_dir, "sites")
                    os.makedirs(sites_dir, exist_ok=True)
                    sites_php_file = os.path.join(sites_dir, "sites.php")
                    if not os.path.exists(sites_php_file):
                        with open(sites_php_file, "w") as sf:
                            sf.write("""<?php
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
                        log("✓ Archivo sites.php con mapeo dinámico multisite creado.")
                    else:
                        log("✓ Archivo sites.php ya presente en el proyecto.")

                # 3. Start containers
                set_st("Iniciando contenedores DDEV...")
                self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                # 4. Dependency install if requested and needed
                if do_composer:
                    vendor_dir = os.path.join(target_dir, "vendor")
                    composer_json = os.path.join(target_dir, "composer.json")
                    if os.path.exists(composer_json) and not os.path.exists(vendor_dir):
                        set_st("Instalando dependencias de Composer...")
                        log("📦 Ejecutando 'ddev composer install'...")
                        self.run_subproc(["ddev", "composer", "install"], target_dir, dialog)
                        log("✓ Dependencias de Composer instaladas.")
                        
                    node_modules = os.path.join(target_dir, "node_modules")
                    package_json = os.path.join(target_dir, "package.json")
                    if os.path.exists(package_json) and not os.path.exists(node_modules) and not os.path.exists(composer_json):
                        set_st("Instalando dependencias de Node.js...")
                        log("📦 Ejecutando 'ddev npm install'...")
                        self.run_subproc(["ddev", "npm", "install"], target_dir, dialog)
                        log("✓ Dependencias de Node.js instaladas.")
                        
                    req_txt = os.path.join(target_dir, "requirements.txt")
                    venv_dir = os.path.join(target_dir, ".venv")
                    if os.path.exists(req_txt) and not os.path.exists(venv_dir):
                        set_st("Configurando entorno virtual Python e instalando dependencias...")
                        log("🐍 Creando .venv e instalando dependencias...")
                        self.run_subproc(["ddev", "exec", "python3 -m venv /var/www/html/.venv && /var/www/html/.venv/bin/pip install -r requirements.txt"], target_dir, dialog)
                        log("✓ Dependencias de Python instaladas.")
                        
                primary_url = f"https://{slug}.ddev.site"
                log("\n" + "="*50)
                log(f"¡Proyecto '{slug}' importado y activado con éxito!")
                log(f"🌐 URL: {primary_url}")
                
                GLib.idle_add(dialog.finish, True, f"¡Proyecto '{slug}' listo!", primary_url, target_dir)
                GLib.idle_add(self.refresh_projects)
                GLib.idle_add(lambda: self.notebook.set_current_page(0))
                
            except Exception as ex:
                log(f"\n❌ ERROR: {str(ex)}")
                GLib.idle_add(dialog.finish, False, f"Error importando proyecto: {str(ex)}", "", target_dir)
                
        threading.Thread(target=run_import, daemon=True).start()

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
        db_type = self.combo_db.get_active_id() or self.combo_db.get_active_text() or fw.get("db", "mariadb:10.11")
        node_version = self.combo_node.get_active_id() or self.combo_node.get_active_text() or fw.get("nodejs", "22")
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

                
                    # Check if Drupal Multisite was requested
                    is_multisite_enabled = getattr(self, "chk_enable_multisite", None) and self.chk_enable_multisite.get_active()
                    if is_multisite_enabled:
                        set_st("Configurando arquitectura Drupal Multisite...")
                        sites_php_dir = os.path.join(target_dir, d_docroot, "sites") if d_docroot else os.path.join(target_dir, "sites")
                        os.makedirs(sites_php_dir, exist_ok=True)
                        sites_php_file = os.path.join(sites_php_dir, "sites.php")
                        with open(sites_php_file, "w") as sf:
                            sf.write('''<?php
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
''')
                        log("✓ Arquitectura Multisite habilitada en sites/sites.php con mapeo dinámico.")

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

                elif fw_id == "django":
                    set_st("Configurando DDEV para Django...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=generic",
                        "--docroot=.",
                        f"--database={db_type}",
                        "--webimage-extra-packages=python3-venv,python3-pip"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    set_st("Iniciando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    set_st("Creando entorno virtual Python (.venv)...")
                    self.run_subproc(["ddev", "exec", "python3 -m venv /var/www/html/.venv"], target_dir, dialog)
                    
                    set_st("Instalando Django y conectores de base de datos...")
                    self.run_subproc(["ddev", "exec", "/var/www/html/.venv/bin/pip install django PyMySQL cryptography psycopg2-binary"], target_dir, dialog)
                    
                    set_st("Generando estructura inicial de Django...")
                    self.run_subproc(["ddev", "exec", "/var/www/html/.venv/bin/django-admin startproject app ."], target_dir, dialog)
                    
                    set_st("Configurando base de datos y ALLOWED_HOSTS...")
                    settings_py_path = os.path.join(target_dir, "app", "settings.py")
                    if os.path.exists(settings_py_path):
                        try:
                            with open(settings_py_path, "r") as sf:
                                s_code = sf.read()
                            s_code = s_code.replace("ALLOWED_HOSTS = []", "ALLOWED_HOSTS = ['*']")
                            if "postgres" in db_type:
                                db_block = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'db',
        'USER': 'db',
        'PASSWORD': 'db',
        'HOST': 'db',
        'PORT': '5432',
    }
}"""
                            else:
                                db_block = """import pymysql
pymysql.install_as_MySQLdb()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db',
        'USER': 'db',
        'PASSWORD': 'db',
        'HOST': 'db',
        'PORT': '3306',
    }
}"""
                            s_code = re.sub(r'DATABASES\s*=\s*\{.*?\n\}', db_block, s_code, flags=re.DOTALL)
                            with open(settings_py_path, "w") as sf:
                                sf.write(s_code)
                        except Exception as ex:
                            log(f"Nota en settings.py: {ex}")
                            
                    set_st("Ejecutando migraciones de base de datos...")
                    self.run_subproc(["ddev", "exec", "/var/www/html/.venv/bin/python manage.py migrate"], target_dir, dialog)
                    
                    if auto_install:
                        set_st("Creando superusuario administrador (admin / admin)...")
                        superuser_script = "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')"
                        self.run_subproc(["ddev", "exec", f'/var/www/html/.venv/bin/python manage.py shell -c "{superuser_script}"'], target_dir, dialog)
                        log("\n👑 Superusuario creado: admin / admin (Panel en /admin)")
                        
                    set_st("Configurando Nginx Reverse Proxy y daemon de fondo...")
                    nginx_full_dir = os.path.join(target_dir, ".ddev", "nginx_full")
                    os.makedirs(nginx_full_dir, exist_ok=True)
                    with open(os.path.join(nginx_full_dir, "nginx-site.conf"), "w") as nf:
                        nf.write("""server {
    listen 80 default_server;
    listen 443 ssl default_server;

    root /var/www/html;

    ssl_certificate /etc/ssl/certs/master.crt;
    ssl_certificate_key /etc/ssl/certs/master.key;

    include /etc/nginx/monitoring.conf;

    error_log /dev/stdout info;
    access_log /var/log/nginx/access.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    include /etc/nginx/common.d/*.conf;
    include /mnt/ddev_config/nginx/*.conf;
}
""")
                    with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                        df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: django
    command: "/var/www/html/.venv/bin/python manage.py runserver 0.0.0.0:8000"
    directory: /var/www/html
""")
                    set_st("Reiniciando servidor DDEV para activar Django...")
                    self.run_subproc(["ddev", "restart", "-y"], target_dir, dialog)
                    log("\n🎉 Proyecto Django listo y corriendo!")

                elif fw_id == "flask":
                    set_st("Configurando DDEV para Flask...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=generic",
                        "--docroot=.",
                        f"--database={db_type}",
                        "--webimage-extra-packages=python3-venv,python3-pip"
                    ]
                    self.run_subproc(cfg_cmd, target_dir, dialog)
                    
                    set_st("Iniciando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    set_st("Creando entorno virtual Python (.venv)...")
                    self.run_subproc(["ddev", "exec", "python3 -m venv /var/www/html/.venv"], target_dir, dialog)
                    
                    set_st("Instalando Flask y conectores...")
                    self.run_subproc(["ddev", "exec", "/var/www/html/.venv/bin/pip install flask pymysql psycopg2-binary cryptography python-dotenv"], target_dir, dialog)
                    
                    set_st("Creando aplicación inicial app.py...")
                    app_py_path = os.path.join(target_dir, "app.py")
                    flask_code = f"""from flask import Flask, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = \"\"\"<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{slug} - Flask en DDEV</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 500px; border: 1px solid rgba(255,255,255,0.1); }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        .badge {{ background: #0284c7; padding: 4px 12px; border-radius: 9999px; font-size: 0.85rem; font-weight: bold; display: inline-block; margin-top: 10px; }}
        p {{ color: #94a3b8; line-height: 1.5; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>¡Flask en DDEV Studio! 🚀</h1>
        <p>Tu aplicación <b>{slug}</b> con microframework Flask está corriendo exitosamente en Ubuntu MATE.</p>
        <span class="badge">Python 3 + Flask + DDEV</span>
    </div>
</body>
</html>\"\"\"

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
"""
                    with open(app_py_path, "w") as f:
                        f.write(flask_code)

                    set_st("Configurando Nginx Reverse Proxy y daemon de fondo...")
                    nginx_full_dir = os.path.join(target_dir, ".ddev", "nginx_full")
                    os.makedirs(nginx_full_dir, exist_ok=True)
                    with open(os.path.join(nginx_full_dir, "nginx-site.conf"), "w") as nf:
                        nf.write("""server {
    listen 80 default_server;
    listen 443 ssl default_server;

    root /var/www/html;

    ssl_certificate /etc/ssl/certs/master.crt;
    ssl_certificate_key /etc/ssl/certs/master.key;

    include /etc/nginx/monitoring.conf;

    error_log /dev/stdout info;
    access_log /var/log/nginx/access.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    include /etc/nginx/common.d/*.conf;
    include /mnt/ddev_config/nginx/*.conf;
}
""")
                    with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                        df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: flask
    command: "/var/www/html/.venv/bin/python app.py"
    directory: /var/www/html
""")
                    set_st("Reiniciando servidor DDEV para activar Flask...")
                    self.run_subproc(["ddev", "restart", "-y"], target_dir, dialog)
                    log("\n🎉 Proyecto Flask listo y corriendo!")

                elif fw_id == "angular":
                    set_st("Configurando DDEV para Angular...")
                    cfg_cmd = [
                        "ddev", "config",
                        f"--project-name={slug}",
                        "--project-type=generic",
                        "--docroot=dist",
                        f"--nodejs-version={node_version}",
                        "--web-environment-add=NG_CLI_ANALYTICS=false"
                    ]
                    if db_type == "none":
                        cfg_cmd.append("--omit-containers=db")
                    else:
                        cfg_cmd.append(f"--database={db_type}")
                    self.run_subproc(cfg_cmd, target_dir, dialog)

                    set_st("Iniciando contenedores DDEV...")
                    self.run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                    
                    set_st("Creando proyecto Angular con @angular/cli...")
                    self.run_subproc(["ddev", "exec", "NG_CLI_ANALYTICS=false npx -y @angular/cli new app --directory=. --routing --style=css --skip-git --defaults"], target_dir, dialog)
                    
                    set_st("Configurando Nginx Reverse Proxy y Live Dev Server...")
                    nginx_full_dir = os.path.join(target_dir, ".ddev", "nginx_full")
                    os.makedirs(nginx_full_dir, exist_ok=True)
                    with open(os.path.join(nginx_full_dir, "nginx-site.conf"), "w") as nf:
                        nf.write("""server {
    listen 80 default_server;
    listen 443 ssl default_server;

    root /var/www/html;

    ssl_certificate /etc/ssl/certs/master.crt;
    ssl_certificate_key /etc/ssl/certs/master.key;

    include /etc/nginx/monitoring.conf;

    error_log /dev/stdout info;
    access_log /var/log/nginx/access.log;

    location / {
        proxy_pass http://127.0.0.1:4200;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    include /etc/nginx/common.d/*.conf;
    include /mnt/ddev_config/nginx/*.conf;
}
""")
                    with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                        df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: angular
    command: "npx ng serve --host 0.0.0.0 --port 4200 --allowed-hosts"
    directory: /var/www/html
""")
                    set_st("Reiniciando DDEV para activar Angular Live Dev Server...")
                    self.run_subproc(["ddev", "restart", "-y"], target_dir, dialog)
                    log("\n🎉 Proyecto Angular listo y corriendo!")

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
    
    # Ensure proper initial framework visibility
    first_child = app.flowbox_fw.get_child_at_index(0)
    if first_child:
        app.on_framework_selected(app.flowbox_fw, first_child)
    if hasattr(app, "combo_import_type"):
        app.on_import_type_changed(app.combo_import_type)
        
    Gtk.main()


if __name__ == "__main__":
    main()
