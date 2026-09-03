# -*- coding: utf-8 -*-
"""
Vista de Creación e Importación de Proyectos para DDEV Studio.
"""

import os
import re
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from ddev_studio.constants import (
    FRAMEWORKS,
    DRUPAL_VERSIONS,
    DEFAULT_SITES_DIR,
)
from ddev_studio.core.detector import detect_project_details, sanitize_project_name
from ddev_studio.recipes.runner import run_create_project, run_import_project
from ddev_studio.ui.helpers import load_icon


class NewProjectView(Gtk.ScrolledWindow):
    """
    Componente desacoplado para el asistente de creación de nuevos proyectos
    e importación de proyectos locales existentes en DDEV.
    """
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_vbox.set_margin_start(24)
        main_vbox.set_margin_end(24)
        main_vbox.set_margin_top(16)
        main_vbox.set_margin_bottom(24)
        self.add(main_vbox)

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

    def switch_mode(self, mode="create"):
        """Permite alternar programáticamente entre 'create' e 'import'."""
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

            if hasattr(self, "lbl_new_php") and hasattr(self, "combo_php"):
                self.lbl_new_php.set_visible(is_php)
                self.combo_php.set_visible(is_php)

            if hasattr(self, "lbl_new_nodejs") and hasattr(self, "combo_node"):
                self.lbl_new_nodejs.set_visible(is_node)
                self.combo_node.set_visible(is_node)

            if hasattr(self, "lbl_new_python") and hasattr(self, "lbl_new_python_info"):
                self.lbl_new_python.set_visible(is_python)
                self.lbl_new_python_info.set_visible(is_python)

            if hasattr(self, "combo_db"):
                curr_db = self.combo_db.get_active_id()
                self.combo_db.remove_all()
                if is_node:
                    self.combo_db.append("none", "Ninguna")
                    self.combo_db.append("sqlite", "SQLite")
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11")
                    self.combo_db.append("postgres:16", "PostgreSQL 16")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.set_active_id("none")
                elif fw_id == "django":
                    self.combo_db.append("sqlite", "SQLite")
                    self.combo_db.append("postgres:16", "PostgreSQL 16 (Producción)")
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.set_active_id("sqlite")
                elif fw_id == "flask":
                    self.combo_db.append("sqlite", "SQLite")
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11")
                    self.combo_db.append("postgres:16", "PostgreSQL 16")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.set_active_id("sqlite")
                elif fw_id == "laravel":
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11 (Recomendada)")
                    self.combo_db.append("sqlite", "SQLite")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.append("postgres:16", "PostgreSQL 16")
                    self.combo_db.set_active_id("mariadb:10.11")
                elif fw_id in ["drupal", "wordpress", "symfony"]:
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11 (Recomendada)")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.append("postgres:16", "PostgreSQL 16")
                    self.combo_db.append("mariadb:10.5", "MariaDB 10.5")
                    self.combo_db.set_active_id("mariadb:10.11")
                else:
                    self.combo_db.append("mariadb:10.11", "MariaDB 10.11 (Recomendada)")
                    self.combo_db.append("sqlite", "SQLite")
                    self.combo_db.append("mysql:8.0", "MySQL 8.0")
                    self.combo_db.append("postgres:16", "PostgreSQL 16")
                    self.combo_db.append("none", "Ninguna")
                    self.combo_db.set_active_id("mariadb:10.11")

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
            parent=self.main_app,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_current_folder(self.entry_path.get_text().strip())
        if dialog.run() == Gtk.ResponseType.OK:
            self.entry_path.set_text(dialog.get_filename())
            self.on_project_name_changed(self.entry_name)
        dialog.destroy()

    def on_browse_import_folder(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar carpeta de proyecto existente",
            parent=self.main_app,
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

        self.combo_import_type.set_active_id(det["type"])

        for idx, text in enumerate(["docroot", "web", "public", "dist", "."]):
            if text == det["docroot"]:
                self.combo_import_docroot.set_active(idx)
                break

        for idx, text in enumerate(["8.3", "8.2", "8.1", "8.4", "8.0", "7.4"]):
            if text == det.get("php", "8.3"):
                self.combo_import_php.set_active(idx)
                break

        if hasattr(self, "combo_import_nodejs") and det.get("nodejs"):
            self.combo_import_nodejs.set_active_id(det["nodejs"])

        self.on_import_type_changed(self.combo_import_type)

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

        if hasattr(self, "lbl_import_php") and hasattr(self, "combo_import_php"):
            self.lbl_import_php.set_visible(is_php)
            self.combo_import_php.set_visible(is_php)

        if hasattr(self, "lbl_import_nodejs") and hasattr(self, "combo_import_nodejs"):
            self.lbl_import_nodejs.set_visible(is_node)
            self.combo_import_nodejs.set_visible(is_node)

        if hasattr(self, "lbl_import_python") and hasattr(self, "lbl_import_python_info"):
            self.lbl_import_python.set_visible(is_python)
            self.lbl_import_python_info.set_visible(is_python)

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
                transient_for=self.main_app,
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
            if self.main_app:
                self.main_app.refresh_projects()
                self.main_app.notebook.set_current_page(0)

        run_import_project(
            parent_window=self.main_app,
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
                transient_for=self.main_app,
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
                transient_for=self.main_app,
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
            if self.main_app:
                self.main_app.refresh_projects()

        run_create_project(
            parent_window=self.main_app,
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
