# -*- coding: utf-8 -*-
"""
Ventana principal de DDEV Studio con HeaderBar, gestión de proyectos, creación e importación.
"""

import json
import os
import re
import subprocess
import threading
import webbrowser
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from ddev_studio.constants import (
    DEFAULT_SITES_DIR,
    CUSTOM_CSS,
    FRAMEWORKS,
    DRUPAL_VERSIONS,
    TECH_CATEGORIES
)
from ddev_studio.core.detector import detect_project_details, inspect_project_stack, sanitize_project_name
from ddev_studio.core.process import run_subproc
from ddev_studio.core.terminal import open_terminal
from ddev_studio.recipes.runner import run_create_project, run_import_project
from ddev_studio.ui.dialogs.progress import ProgressDialog
from ddev_studio.ui.helpers import load_icon, create_icon_menu_item
from ddev_studio.ui.views.details import ProjectDetailsView
from ddev_studio.ui.views.subsites import SubsitesManagerView


class DDEVManagerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="DDEV Studio")
        self.set_default_size(960, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        ddev_icon = load_icon("ddev.svg", 64)
        if ddev_icon:
            self.set_icon(ddev_icon)
            
        self.active_category = "all"
        self.category_buttons = {}
        
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
        header.props.subtitle = ""
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
            self.on_import_type_changed(self.combo_import_type)
        else:
            self.stack_new_project.set_visible_child_name("create")
            fc = self.flowbox_fw.get_child_at_index(0)
            if fc:
                self.on_framework_selected(self.flowbox_fw, fc)

    def build_tab_new_project(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_vbox.set_margin_start(24)
        main_vbox.set_margin_end(24)
        main_vbox.set_margin_top(16)
        main_vbox.set_margin_bottom(24)
        scrolled.add(main_vbox)
        
        # Mode Selector (Segmented Capsule Switcher)
        mode_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        mode_container.set_halign(Gtk.Align.CENTER)
        mode_container.set_margin_bottom(8)
        
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        mode_box.get_style_context().add_class("segmented-mode-container")
        mode_box.set_halign(Gtk.Align.CENTER)
        
        self.btn_mode_create = Gtk.RadioButton()
        self.btn_mode_create.set_mode(False)
        self.btn_mode_create.get_style_context().add_class("segmented-mode-btn")
        b_create_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_create_box.pack_start(Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_create_box.pack_start(Gtk.Label(label="Descargar Proyecto Nuevo"), False, False, 0)
        self.btn_mode_create.add(b_create_box)
        self.btn_mode_create.connect("toggled", self.on_project_mode_toggled)
        mode_box.pack_start(self.btn_mode_create, False, False, 0)
        
        self.btn_mode_import = Gtk.RadioButton(group=self.btn_mode_create)
        self.btn_mode_import.set_mode(False)
        self.btn_mode_import.get_style_context().add_class("segmented-mode-btn")
        b_import_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_import_box.pack_start(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_import_box.pack_start(Gtk.Label(label="Importar Carpeta Existente"), False, False, 0)
        self.btn_mode_import.add(b_import_box)
        self.btn_mode_import.connect("toggled", self.on_project_mode_toggled)
        mode_box.pack_start(self.btn_mode_import, False, False, 0)
        
        mode_container.pack_start(mode_box, False, False, 0)
        main_vbox.pack_start(mode_container, False, False, 0)
        
        # Stack to switch between Create and Import forms
        self.stack_new_project = Gtk.Stack()
        self.stack_new_project.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack_new_project.set_transition_duration(150)
        
        self.box_create_view = self.build_create_project_view()
        self.stack_new_project.add_named(self.box_create_view, "create")
        
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
        
        # Dedicated Drupal Version Selector Box
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
        
        self.drupal_version_box.show_all()
        self.drupal_version_box.set_no_show_all(True)
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
        
        # PHP Version
        self.lbl_new_php = Gtk.Label(label="Versión de PHP:", halign=Gtk.Align.END)
        self.lbl_new_php.set_no_show_all(True)
        grid_adv.attach(self.lbl_new_php, 0, 0, 1, 1)
        self.combo_php = Gtk.ComboBoxText()
        self.combo_php.set_no_show_all(True)
        for v in ["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]:
            self.combo_php.append_text(v)
        self.combo_php.set_active(0)
        grid_adv.attach(self.combo_php, 1, 0, 1, 1)

        # Node.js Version
        self.lbl_new_nodejs = Gtk.Label(label="Versión de Node.js:", halign=Gtk.Align.END)
        self.lbl_new_nodejs.set_no_show_all(True)
        grid_adv.attach(self.lbl_new_nodejs, 0, 0, 1, 1)
        self.combo_node = Gtk.ComboBoxText()
        self.combo_node.set_no_show_all(True)
        for n in ["22", "20", "18"]:
            self.combo_node.append(n, f"Node.js v{n}")
        self.combo_node.set_active_id("22")
        grid_adv.attach(self.combo_node, 1, 0, 1, 1)

        # Python Runtime Info
        self.lbl_new_python = Gtk.Label(label="Entorno de Ejecución:", halign=Gtk.Align.END)
        self.lbl_new_python.set_no_show_all(True)
        grid_adv.attach(self.lbl_new_python, 0, 0, 1, 1)
        self.lbl_new_python_info = Gtk.Label(halign=Gtk.Align.START)
        self.lbl_new_python_info.set_no_show_all(True)
        self.lbl_new_python_info.set_markup("<span color='#38bdf8'><b>🐍 Python 3.x con entorno virtual .venv aislado</b></span>")
        grid_adv.attach(self.lbl_new_python_info, 1, 0, 1, 1)
        
        # Database
        self.lbl_new_db = Gtk.Label(label="Base de datos:", halign=Gtk.Align.END)
        grid_adv.attach(self.lbl_new_db, 0, 1, 1, 1)
        self.combo_db = Gtk.ComboBoxText()
        grid_adv.attach(self.combo_db, 1, 1, 1, 1)
        
        # Auto install checkbox
        self.chk_auto_install = Gtk.CheckButton(label="Instalar CMS y crear superusuario administrador (admin / admin)")
        self.chk_auto_install.set_no_show_all(True)
        self.chk_auto_install.set_active(True)
        exp_box.pack_start(self.chk_auto_install, False, False, 0)
        
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
            ("nextjs", "Next.js (React Full-Stack)"),
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
        
        # PHP Runtime
        self.lbl_import_php = Gtk.Label(label="Versión de PHP:", halign=Gtk.Align.END)
        self.lbl_import_php.set_no_show_all(True)
        grid_cfg.attach(self.lbl_import_php, 0, 3, 1, 1)
        self.combo_import_php = Gtk.ComboBoxText()
        self.combo_import_php.set_no_show_all(True)
        for v in ["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]:
            self.combo_import_php.append_text(v)
        self.combo_import_php.set_active(0)
        grid_cfg.attach(self.combo_import_php, 1, 3, 1, 1)

        # Node.js Runtime
        self.lbl_import_nodejs = Gtk.Label(label="Versión de Node.js:", halign=Gtk.Align.END)
        self.lbl_import_nodejs.set_no_show_all(True)
        grid_cfg.attach(self.lbl_import_nodejs, 0, 3, 1, 1)
        self.combo_import_nodejs = Gtk.ComboBoxText()
        self.combo_import_nodejs.set_no_show_all(True)
        for nv in ["22", "20", "18"]:
            self.combo_import_nodejs.append(nv, f"Node.js v{nv}")
        self.combo_import_nodejs.set_active_id("22")
        grid_cfg.attach(self.combo_import_nodejs, 1, 3, 1, 1)

        # Python Runtime
        self.lbl_import_python = Gtk.Label(label="Entorno de Ejecución:", halign=Gtk.Align.END)
        self.lbl_import_python.set_no_show_all(True)
        grid_cfg.attach(self.lbl_import_python, 0, 3, 1, 1)
        self.lbl_import_python_info = Gtk.Label(halign=Gtk.Align.START)
        self.lbl_import_python_info.set_no_show_all(True)
        self.lbl_import_python_info.set_markup("<span color='#38bdf8'><b>🐍 Python 3.x con entorno .venv aislado</b></span>")
        grid_cfg.attach(self.lbl_import_python_info, 1, 3, 1, 1)
        
        # Database
        grid_cfg.attach(Gtk.Label(label="Base de Datos:", halign=Gtk.Align.END), 0, 4, 1, 1)
        self.combo_import_db = Gtk.ComboBoxText()
        grid_cfg.attach(self.combo_import_db, 1, 4, 1, 1)
        
        # Options box
        self.box_import_drupal_options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.chk_import_multisite = Gtk.CheckButton(label="Habilitar arquitectura Drupal Multisite (Configurar sites.php dinámico)")
        self.chk_import_multisite.set_active(True)
        self.box_import_drupal_options.pack_start(self.chk_import_multisite, False, False, 0)
        
        lbl_ms_hint = Gtk.Label()
        lbl_ms_hint.set_markup("<small><span color='#94a3b8'>Permite crear múltiples marcas y subsitios con bases de datos y dominios independientes en este proyecto.</span></small>")
        lbl_ms_hint.set_halign(Gtk.Align.START)
        self.box_import_drupal_options.pack_start(lbl_ms_hint, False, False, 0)
        
        self.box_import_drupal_options.show_all()
        self.box_import_drupal_options.set_no_show_all(True)
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
        self.on_import_type_changed(self.combo_import_type)
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
            is_node = fw_id in ["nextjs", "angular", "react", "vue", "generic"]
            is_python = fw_id in ["django", "flask"]
            
            # Show/hide Drupal version selector
            if hasattr(self, "drupal_version_box"):
                self.drupal_version_box.set_visible(is_drupal)
                if is_drupal:
                    self.on_drupal_version_changed(self.combo_drupal_ver)
            
            if not is_drupal:
                php_val = self.selected_framework.get("php", "8.3")
                for idx, text in enumerate(["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]):
                    if text == php_val:
                        self.combo_php.set_active(idx)
                        break

            # Runtime fields visibility in Advanced Options
            if hasattr(self, "lbl_new_php") and hasattr(self, "combo_php"):
                self.lbl_new_php.set_visible(is_php)
                self.combo_php.set_visible(is_php)
                    
            if hasattr(self, "lbl_new_nodejs") and hasattr(self, "combo_node"):
                self.lbl_new_nodejs.set_visible(is_node)
                self.combo_node.set_visible(is_node)
                    
            if hasattr(self, "lbl_new_python") and hasattr(self, "lbl_new_python_info"):
                self.lbl_new_python.set_visible(is_python)
                self.lbl_new_python_info.set_visible(is_python)

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
                    self.chk_auto_install.set_visible(True)
                    self.chk_auto_install.set_active(True)
                elif fw_id == "wordpress":
                    self.chk_auto_install.set_label("Instalar WordPress y crear usuario administrador (admin / admin)")
                    self.chk_auto_install.set_visible(True)
                    self.chk_auto_install.set_active(True)
                elif fw_id == "django":
                    self.chk_auto_install.set_label("Crear superusuario (admin / admin) y ejecutar migraciones iniciales")
                    self.chk_auto_install.set_visible(True)
                    self.chk_auto_install.set_active(True)
                else:
                    self.chk_auto_install.set_visible(False)

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
        slug = sanitize_project_name(raw_name)
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
        self.stack_projects_tab = Gtk.Stack()
        self.stack_projects_tab.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack_projects_tab.set_transition_duration(200)
        
        # View 1: Main Projects List
        self.box_projects_list_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box_projects_list_view.set_margin_start(16)
        self.box_projects_list_view.set_margin_end(16)
        self.box_projects_list_view.set_margin_top(14)
        self.box_projects_list_view.set_margin_bottom(14)
        
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
        
        self.box_projects_list_view.pack_start(search_box, False, False, 0)
        
        # Barra horizontal de chips de categorías con iconos SVG
        self.categories_scroller = Gtk.ScrolledWindow()
        self.categories_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.categories_scroller.get_style_context().add_class("category-chips-scroller")
        self.categories_scroller.set_min_content_height(38)
        
        self.categories_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.categories_scroller.add(self.categories_box)
        self.box_projects_list_view.pack_start(self.categories_scroller, False, False, 0)
        
        self.projects_scrolled = Gtk.ScrolledWindow()
        self.projects_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.projects_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.projects_scrolled.add(self.projects_list_box)
        self.box_projects_list_view.pack_start(self.projects_scrolled, True, True, 0)
        
        self.stack_projects_tab.add_named(self.box_projects_list_view, "list")
        
        # View 2: Subsites Manager Embedded View
        self.subsites_manager_view = SubsitesManagerView(self)
        self.stack_projects_tab.add_named(self.subsites_manager_view, "subsites")
        
        # View 3: Project Details Embedded View
        self.project_details_view = ProjectDetailsView(self)
        self.stack_projects_tab.add_named(self.project_details_view, "details")
        
        return self.stack_projects_tab

    def refresh_projects(self):
        for child in self.projects_list_box.get_children():
            self.projects_list_box.remove(child)
            
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
        lbl_title.set_markup("<span size='large' weight='600'>Cargando proyectos...</span>")
        lbl_title.set_halign(Gtk.Align.CENTER)
        loader_box.pack_start(lbl_title, False, False, 0)
        
        lbl_sub = Gtk.Label()
        lbl_sub.set_markup("<span color='#94a3b8' size='medium'>Consultando estado de DDEV</span>")
        lbl_sub.set_halign(Gtk.Align.CENTER)
        loader_box.pack_start(lbl_sub, False, False, 0)
        
        self.projects_list_box.pack_start(loader_box, True, True, 0)
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

    def determine_project_category(self, proj, tech_type=""):
        if not tech_type:
            approot = proj.get("approot", "")
            tech_type, _, _, _, _, _ = inspect_project_stack(approot, proj, proj)
        ptype = str(tech_type).lower()
        ddev_type = str(proj.get("type", "")).lower()
        
        for cat in TECH_CATEGORIES:
            if cat["id"] == "all":
                continue
            for k in cat["match_keys"]:
                if k in ptype or k in ddev_type:
                    return cat["id"]
        return "php"

    def set_active_category(self, cat_id):
        self.active_category = cat_id
        for cid, btn in self.category_buttons.items():
            if cid == cat_id:
                btn.get_style_context().add_class("category-chip-active")
            else:
                btn.get_style_context().remove_class("category-chip-active")
        self.apply_project_filters()

    def update_projects_ui(self, projects):
        for child in self.projects_list_box.get_children():
            self.projects_list_box.remove(child)
            
        self.lbl_proj_title.set_text(f"Mis Proyectos ({len(projects)})")
        
        # Calcular conteos por categoría de tecnología
        cat_counts = {"all": len(projects)}
        for p in projects:
            approot = p.get("approot", "")
            tech_type, _, _, _, _, _ = inspect_project_stack(approot, p, p)
            p["_tech_type"] = tech_type
            cat_id = self.determine_project_category(p, tech_type)
            p["_tech_family"] = cat_id
            cat_counts[cat_id] = cat_counts.get(cat_id, 0) + 1
            
        # Reconstruir botones de chip con iconos SVG
        for child in self.categories_box.get_children():
            self.categories_box.remove(child)
        self.category_buttons = {}
        
        if self.active_category != "all" and cat_counts.get(self.active_category, 0) == 0:
            self.active_category = "all"
            
        if projects:
            self.categories_scroller.show()
            for cat in TECH_CATEGORIES:
                cat_id = cat["id"]
                count = cat_counts.get(cat_id, 0)
                if cat_id != "all" and count == 0:
                    continue
                    
                btn = Gtk.Button()
                btn.get_style_context().add_class("category-chip")
                if self.active_category == cat_id:
                    btn.get_style_context().add_class("category-chip-active")
                    
                btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                
                icon_pixbuf = load_icon(cat["icon"], 16)
                if icon_pixbuf:
                    btn_content.pack_start(Gtk.Image.new_from_pixbuf(icon_pixbuf), False, False, 0)
                    
                btn_content.pack_start(Gtk.Label(label=cat["name"]), False, False, 0)
                
                lbl_cnt = Gtk.Label(label=str(count))
                lbl_cnt.get_style_context().add_class("category-chip-count")
                btn_content.pack_start(lbl_cnt, False, False, 0)
                
                btn.add(btn_content)
                btn.connect("clicked", lambda b, c=cat_id: self.set_active_category(c))
                self.categories_box.pack_start(btn, False, False, 0)
                self.category_buttons[cat_id] = btn
            self.categories_box.show_all()
        else:
            self.categories_scroller.hide()
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
        self.apply_project_filters()

    def create_project_item(self, proj):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        card.get_style_context().add_class("project-card")
        card.project_data = proj
        
        approot = proj.get("approot", "")
        tech_type, has_db, is_php, is_python, is_js, is_static = inspect_project_stack(approot, proj, proj)
        ptype = tech_type.lower()
        
        card.tech_family = proj.get("_tech_family") or self.determine_project_category(proj, tech_type)
        
        icon_name = "php.svg"
        if "next" in ptype:
            icon_name = "nextjs.svg"
        elif "wordpress" in ptype:
            icon_name = "wordpress.svg"
        elif "drupal" in ptype:
            icon_name = "drupal.svg"
        elif "laravel" in ptype:
            icon_name = "laravel.svg"
        elif "django" in ptype:
            icon_name = "django.svg"
        elif "flask" in ptype:
            icon_name = "flask.svg"
        elif "angular" in ptype:
            icon_name = "angular.svg"
        elif "react" in ptype:
            icon_name = "react.svg"
        elif "vue" in ptype:
            icon_name = "vue.svg"
        elif "symfony" in ptype:
            icon_name = "symfony.svg"
        elif "python" in ptype:
            icon_name = "python.svg"
        elif is_js:
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
        approot = proj.get("approot", "")
        exists_on_disk = approot and os.path.exists(approot)
        is_missing = ("missing" in status) or (not exists_on_disk)
        
        lbl_status = Gtk.Label()
        lbl_status.get_style_context().add_class("badge")
        if is_missing:
            lbl_status.set_label("CARPETA NO ENCONTRADA")
            lbl_status.get_style_context().add_class("badge-danger")
        elif "running" in status or "ok" in status:
            lbl_status.set_label(status.upper())
            lbl_status.get_style_context().add_class("badge-running")
        elif "paused" in status:
            lbl_status.set_label(status.upper())
            lbl_status.get_style_context().add_class("badge-paused")
        else:
            lbl_status.set_label(status.upper())
            lbl_status.get_style_context().add_class("badge-stopped")
        title_row.pack_start(lbl_status, False, False, 0)
        
        lbl_type = Gtk.Label(label=tech_type.upper())
        lbl_type.get_style_context().add_class("badge")
        lbl_type.get_style_context().add_class("badge-tech")
        title_row.pack_start(lbl_type, False, False, 0)
        
        is_drupal = "drupal" in ptype or (approot and (os.path.exists(os.path.join(approot, "docroot", "sites")) or os.path.exists(os.path.join(approot, "web", "sites")) or os.path.exists(os.path.join(approot, "sites"))))
        if is_drupal:
            subsite_count = 0
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
                lbl_drupal_mode.set_label("DRUPAL SITE")
                lbl_drupal_mode.get_style_context().add_class("badge-single-site")
                lbl_drupal_mode.set_tooltip_text("Drupal Single Site (Sitio estándar individual)")
            title_row.pack_start(lbl_drupal_mode, False, False, 0)
        
        info_box.pack_start(title_row, False, False, 0)
        
        primary_url = proj.get("primary_url") or proj.get("httpsurl") or proj.get("httpurl") or ""
        lbl_url = Gtk.Label()
        if primary_url and not is_missing:
            lbl_url.set_markup(f"🌐 <a href='{primary_url}'><b>{primary_url}</b></a>")
        else:
            lbl_url.set_markup("<span color='#9ca3af'>🌐 Sin URL activa</span>")
        lbl_url.set_halign(Gtk.Align.START)
        info_box.pack_start(lbl_url, False, False, 0)
        
        lbl_path = Gtk.Label()
        if is_missing:
            lbl_path.set_markup(f"<small><span color='#ef4444'>⚠️ <b>Carpeta no encontrada en disco:</b> {approot}</span></small>")
        elif approot:
            lbl_path.set_markup(f"<small><span color='#94a3b8'>📁 <b>Ubicación:</b> {approot}</span></small>")
        else:
            lbl_path.set_markup("<small><span color='#94a3b8'>📁 <i>Ubicación no disponible</i></span></small>")
        lbl_path.set_halign(Gtk.Align.START)
        info_box.pack_start(lbl_path, False, False, 0)
        
        card.pack_start(info_box, True, True, 0)
        
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions_box.set_valign(Gtk.Align.CENTER)
        
        if is_missing:
            btn_del_orphan = Gtk.Button()
            btn_del_orphan.get_style_context().add_class("btn-primary")
            b_del_orphan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_del_orphan_box.pack_start(Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_del_orphan_box.pack_start(Gtk.Label(label="Desregistrar / Eliminar"), False, False, 0)
            btn_del_orphan.add(b_del_orphan_box)
            btn_del_orphan.set_tooltip_text("Desregistrar y eliminar proyecto huérfano de DDEV (ddev stop --unlist / delete)")
            btn_del_orphan.connect("clicked", lambda b, p=proj: self.confirm_delete_project(p))
            actions_box.pack_start(btn_del_orphan, False, False, 0)
            
            card.pack_start(actions_box, False, False, 0)
            return card
        actions_box.set_valign(Gtk.Align.CENTER)
        
        is_running = "running" in status or "ok" in status
        
        btn_toggle = Gtk.Button()
        btn_t_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        if is_running:
            btn_t_box.pack_start(Gtk.Image.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.MENU), False, False, 0)
            btn_t_box.pack_start(Gtk.Label(label="Detener"), False, False, 0)
            btn_toggle.add(btn_t_box)
            btn_toggle.set_tooltip_text("Detener proyecto (ddev stop)")
            btn_toggle.connect("clicked", lambda b, p=proj: self.execute_simple_action("stop", p))
        else:
            btn_t_box.pack_start(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.MENU), False, False, 0)
            btn_t_box.pack_start(Gtk.Label(label="Iniciar"), False, False, 0)
            btn_toggle.add(btn_t_box)
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
            b_sub_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            b_sub_box.pack_start(Gtk.Image.new_from_icon_name("network-server-symbolic", Gtk.IconSize.MENU), False, False, 0)
            sub_txt = f"Subsitios ({subsite_count})" if is_multisite and subsite_count > 0 else "Subsitios"
            b_sub_box.pack_start(Gtk.Label(label=sub_txt), False, False, 0)
            btn_subsites.add(b_sub_box)
            if is_multisite and subsite_count > 0:
                btn_subsites.set_tooltip_text(f"Gestionar los {subsite_count} subsitios de este Drupal Multisite")
            else:
                btn_subsites.set_tooltip_text("Gestionar o aprovisionar subsitios multisite para este proyecto")
            btn_subsites.connect("clicked", lambda b, p=proj: self.open_subsites_manager(p))
            actions_box.pack_start(btn_subsites, False, False, 0)
            
            # Reconstruir/Limpiar Caché
            btn_quick_cr = Gtk.Button()
            b_cr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            b_cr_box.pack_start(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_cr_box.pack_start(Gtk.Label(label="Caché"), False, False, 0)
            btn_quick_cr.add(b_cr_box)
            btn_quick_cr.get_style_context().add_class("btn-quick")
            btn_quick_cr.get_style_context().add_class("btn-quick-cache")
            btn_quick_cr.set_tooltip_text("Reconstruir caché de Drupal (ddev drush cr)")
            btn_quick_cr.connect("clicked", lambda b, p=proj: self.execute_drush_action("cr", p))
            actions_box.pack_start(btn_quick_cr, False, False, 0)
            
            # One-Time Login
            btn_quick_uli = Gtk.Button()
            b_uli_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            b_uli_box.pack_start(Gtk.Image.new_from_icon_name("dialog-password-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_uli_box.pack_start(Gtk.Label(label="Login"), False, False, 0)
            btn_quick_uli.add(b_uli_box)
            btn_quick_uli.get_style_context().add_class("btn-quick")
            btn_quick_uli.get_style_context().add_class("btn-quick-login")
            btn_quick_uli.set_tooltip_text("Iniciar sesión como Administrador (ddev drush uli)")
            btn_quick_uli.connect("clicked", lambda b, p=proj: self.execute_drush_action("uli", p))
            actions_box.pack_start(btn_quick_uli, False, False, 0)
            
            # Menú desplegable completo de herramientas Drush
            menu_btn_drush = Gtk.MenuButton()
            menu_btn_drush.set_tooltip_text("Menú de comandos de Drupal / Drush")
            menu_btn_drush.get_style_context().add_class("btn-drupal")
            b_drush_lbl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            b_drush_lbl.pack_start(Gtk.Label(label="Drush"), False, False, 0)
            b_drush_lbl.pack_start(Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.MENU), False, False, 0)
            menu_btn_drush.add(b_drush_lbl)
            
            drush_menu = Gtk.Menu()
            drush_menu.append(create_icon_menu_item("dialog-password-symbolic", "Iniciar Sesión Admin (drush uli)", lambda w, pr=proj: self.execute_drush_action("uli", pr)))
            drush_menu.append(create_icon_menu_item("view-refresh-symbolic", "Limpiar / Reconstruir Caché (drush cr)", lambda w, pr=proj: self.execute_drush_action("cr", pr)))
            drush_menu.append(create_icon_menu_item("software-update-available-symbolic", "Actualizar Base de Datos (drush updb)", lambda w, pr=proj: self.execute_drush_action("updb", pr)))
            
            drush_menu.append(Gtk.SeparatorMenuItem())
            drush_menu.append(create_icon_menu_item("go-down-symbolic", "Importar Base de Datos (.sql / .sql.gz)", lambda w, pr=proj: self.execute_drush_action("import_db", pr)))
            drush_menu.append(create_icon_menu_item("go-up-symbolic", "Exportar Base de Datos (.sql.gz)", lambda w, pr=proj: self.execute_drush_action("export_db", pr)))
            drush_menu.append(Gtk.SeparatorMenuItem())
            
            if "drupal7" not in ptype:
                drush_menu.append(create_icon_menu_item("document-save-symbolic", "Exportar Configuración (drush cex)", lambda w, pr=proj: self.execute_drush_action("cex", pr)))
                drush_menu.append(create_icon_menu_item("document-open-symbolic", "Importar Configuración (drush cim)", lambda w, pr=proj: self.execute_drush_action("cim", pr)))
                drush_menu.append(Gtk.SeparatorMenuItem())
                
            drush_menu.append(create_icon_menu_item("alarm-symbolic", "Ejecutar Cron (drush cron)", lambda w, pr=proj: self.execute_drush_action("cron", pr)))
            drush_menu.append(create_icon_menu_item("dialog-information-symbolic", "Estado del Sitio (drush status)", lambda w, pr=proj: self.execute_drush_action("status", pr)))
            drush_menu.append(create_icon_menu_item("text-x-generic-symbolic", "Ver Logs Recientes (drush watchdog)", lambda w, pr=proj: self.execute_drush_action("watchdog", pr)))
            drush_menu.append(create_icon_menu_item("application-x-addon-symbolic", "Módulos Habilitados (drush pm:list)", lambda w, pr=proj: self.execute_drush_action("pm_list", pr)))
            
            drush_menu.append(Gtk.SeparatorMenuItem())
            drush_menu.append(create_icon_menu_item("utilities-terminal-symbolic", "Abrir SSH en Contenedor (ddev ssh)", lambda w, pr=proj: self.execute_drush_action("ssh", pr)))
            drush_menu.append(create_icon_menu_item("system-software-install-symbolic", "Instalar Drush si falta (composer require)", lambda w, pr=proj: self.execute_drush_action("install_drush", pr)))
            
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
            
        btn_details = Gtk.Button()
        btn_details.add(Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.BUTTON))
        btn_details.set_tooltip_text("Ver detalles, servicios y credenciales de este proyecto (ddev describe)")
        btn_details.connect("clicked", lambda b, p=proj: self.open_project_details(p))
        actions_box.pack_start(btn_details, False, False, 0)
        
        btn_del = Gtk.Button()
        btn_del.add(Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON))
        btn_del.set_tooltip_text("Eliminar proyecto DDEV")
        btn_del.connect("clicked", lambda b, p=proj: self.confirm_delete_project(p))
        actions_box.pack_start(btn_del, False, False, 0)
        
        card.pack_start(actions_box, False, False, 0)
        return card

    def open_terminal(self, path, command=""):
        open_terminal(path, command)

    def on_search_changed(self, entry):
        self.apply_project_filters()

    def apply_project_filters(self):
        query = self.search_entry.get_text().strip().lower()
        for child in self.projects_list_box.get_children():
            if hasattr(child, "project_data"):
                p = child.project_data
                name = p.get("name", "").lower()
                ptype = str(p.get("type", "")).lower()
                tech_type = str(p.get("_tech_type", "")).lower()
                url = str(p.get("primary_url", "")).lower()
                
                # Category filter
                family = getattr(child, "tech_family", "all")
                match_cat = (self.active_category == "all") or (family == self.active_category)
                
                # Search query filter
                match_query = not query or (query in name) or (query in ptype) or (query in tech_type) or (query in url)
                
                child.set_visible(match_cat and match_query)

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
        exists_on_disk = bool(approot and os.path.exists(approot))
        
        dialog = ProgressDialog(self, title=f"{action.capitalize()} {pname}")
        dialog.set_status(f"Ejecutando ddev {action} en {pname}...")
        
        def task():
            try:
                cmd = ["ddev"] + action.split()
                if "delete" in action or not exists_on_disk:
                    if pname and pname not in cmd:
                        cmd.append(pname)
                    if "-y" not in cmd and "delete" in action:
                        cmd.append("-y")
                    effective_cwd = approot if exists_on_disk else None
                else:
                    effective_cwd = approot
                
                cmd_str = " ".join(cmd)
                GLib.idle_add(dialog.append_log, f"$ {cmd_str}\n")
                
                process = subprocess.Popen(
                    cmd,
                    cwd=effective_cwd,
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
                
                # If ddev delete -O failed on an orphaned project, fallback to ddev stop --unlist
                if not success and ("delete" in action or not exists_on_disk):
                    GLib.idle_add(dialog.append_log, f"\nIntentando desregistrar con 'ddev stop --unlist {pname}'...\n")
                    p_fallback = subprocess.run(["ddev", "stop", "--unlist", pname], capture_output=True, text=True)
                    if p_fallback.stdout:
                        GLib.idle_add(dialog.append_log, p_fallback.stdout + "\n")
                    if p_fallback.returncode == 0:
                        success = True
                
                url = proj.get("primary_url", "") if "start" in action else ""
                msg = f"Proyecto {pname} {action} con éxito" if success else f"Error al ejecutar {action}"
                GLib.idle_add(dialog.finish, success, msg, url, approot)
                GLib.idle_add(self.refresh_projects)
            except Exception as ex:
                GLib.idle_add(dialog.append_log, f"\nExcepción: {str(ex)}\n")
                GLib.idle_add(dialog.finish, False, f"Error: {str(ex)}", "", approot)
                GLib.idle_add(self.refresh_projects)
            
        threading.Thread(target=task, daemon=True).start()

    def confirm_delete_project(self, proj):
        pname = proj.get("name", "")
        approot = proj.get("approot", "")
        exists_on_disk = bool(approot and os.path.exists(approot))
        
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"¿Estás seguro de eliminar '{pname}'?"
        )
        if not exists_on_disk:
            dialog.format_secondary_text(
                f"La carpeta local de este proyecto ({approot}) no existe en el disco.\n\n"
                f"DDEV detendrá y desregistrará cualquier contenedor o registro huérfano asociado a '{pname}'."
            )
        else:
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
        self.subsites_manager_view.load_project(proj)
        self.stack_projects_tab.set_visible_child_name("subsites")

    def open_project_details(self, proj):
        self.project_details_view.load_project_details(proj)
        self.stack_projects_tab.set_visible_child_name("details")

    def on_export_db(self, widget, proj):
        approot = proj.get("approot", "")
        pname = proj.get("name", "")
        self.project_details_view.on_export_db_clicked(approot, pname)

    def on_import_db(self, widget, proj):
        approot = proj.get("approot", "")
        pname = proj.get("name", "")
        self.project_details_view.on_import_db_clicked(approot, pname)

    def show_projects_list(self):
        self.stack_projects_tab.set_visible_child_name("list")
        self.refresh_projects()

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
        is_node = t_id in ["angular", "react", "vue", "nextjs", "generic"]
        is_python = t_id in ["django", "flask"]
        
        if hasattr(self, "box_import_drupal_options"):
            self.box_import_drupal_options.set_visible(is_dr)
            
        # Runtime visibility
        if hasattr(self, "lbl_import_php") and hasattr(self, "combo_import_php"):
            self.lbl_import_php.set_visible(is_php)
            self.combo_import_php.set_visible(is_php)
                
        if hasattr(self, "lbl_import_nodejs") and hasattr(self, "combo_import_nodejs"):
            self.lbl_import_nodejs.set_visible(is_node)
            self.combo_import_nodejs.set_visible(is_node)
                
        if hasattr(self, "lbl_import_python") and hasattr(self, "lbl_import_python_info"):
            self.lbl_import_python.set_visible(is_python)
            self.lbl_import_python_info.set_visible(is_python)
            
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
            self.chk_import_composer.set_visible(True)

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
        slug = sanitize_project_name(raw_name)
        if not slug:
            slug = sanitize_project_name(os.path.basename(target_dir.rstrip("/")))
            
        p_type = self.combo_import_type.get_active_id() or "drupal10"
        docroot = self.combo_import_docroot.get_active_text() or "docroot"
        php_ver = self.combo_import_php.get_active_text() or "8.3"
        raw_node = self.combo_import_nodejs.get_active_id() if hasattr(self, "combo_import_nodejs") else "22"
        if not raw_node and hasattr(self, "combo_import_nodejs"):
            raw_node = self.combo_import_nodejs.get_active_text()
        node_ver = re.sub(r'[^\d]', '', str(raw_node or '')) or "22"
        db_type = self.combo_import_db.get_active_id() or "mariadb:10.11"
        is_multisite = ("drupal" in p_type) and self.chk_import_multisite.get_active()
        do_composer = self.chk_import_composer.get_active()
        
        def on_success():
            self.refresh_projects()
            self.notebook.set_current_page(0)
            
        run_import_project(
            parent_window=self,
            target_dir=target_dir,
            slug=slug,
            p_type=p_type,
            docroot=docroot,
            php_ver=php_ver,
            node_ver=node_ver,
            db_type=db_type,
            is_multisite=is_multisite,
            do_composer=do_composer,
            on_success_callback=on_success
        )

    def on_create_project_clicked(self, widget):
        raw_name = self.entry_name.get_text().strip()
        slug = sanitize_project_name(raw_name)
        if not slug:
            msg_diag = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Por favor ingresa un nombre válido para el proyecto"
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
        
        drupal_ver_info = DRUPAL_VERSIONS[0]
        if fw_id == "drupal":
            idx = self.combo_drupal_ver.get_active()
            if 0 <= idx < len(DRUPAL_VERSIONS):
                drupal_ver_info = DRUPAL_VERSIONS[idx]

        php_version = self.combo_php.get_active_text() or fw.get("php", "8.3")
        db_type = self.combo_db.get_active_id() or self.combo_db.get_active_text() or fw.get("db", "mariadb:10.11")
        raw_node = self.combo_node.get_active_id() or self.combo_node.get_active_text() or "22"
        node_version = re.sub(r'[^\d]', '', str(raw_node or '')) or "22"
        auto_install = self.chk_auto_install.get_active()
        is_multisite_enabled = getattr(self, "chk_enable_multisite", None) and self.chk_enable_multisite.get_active()
        
        def on_success():
            self.refresh_projects()
            
        run_create_project(
            parent_window=self,
            raw_name=raw_name,
            base_dir=base_dir,
            clean_target_before=clean_target_before,
            fw=fw,
            drupal_ver_info=drupal_ver_info,
            php_version=php_version,
            db_type=db_type,
            node_version=node_version,
            auto_install=auto_install,
            is_multisite_enabled=is_multisite_enabled,
            on_success_callback=on_success
        )

    def run_subproc(self, cmd, cwd, dialog):
        return run_subproc(cmd, cwd, dialog)
