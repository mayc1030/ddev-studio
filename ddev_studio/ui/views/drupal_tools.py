# -*- coding: utf-8 -*-
"""
Vista embebida de asistente dedicado para Drupal: Scaffolding de código (Drush Generate),
Suite de APIs REST / JSON:API / OAuth2 y generador de endpoints custom.
Integrada en el Gtk.Stack de navegación principal (estilo vista de Detalle).
"""

import os
import threading
import webbrowser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ddev_studio.core.detector import read_ddev_config
from ddev_studio.core.drupal_tools import (
    sanitize_machine_name,
    scan_custom_modules,
    scan_custom_themes,
    check_drupal_api_status,
    build_drush_generate_command,
    build_starterkit_theme_command,
    build_subtheme_command,
    is_theme_installed,
    DRUPAL_BASE_THEMES_PRESETS,
    scaffold_custom_module,
    scaffold_custom_theme,
    scaffold_custom_component,
    scaffold_rest_resource,
    get_drupal_uninstall_anchor,
    get_drupal_uninstall_url
)
from ddev_studio.core.terminal import open_terminal
from ddev_studio.core.process import run_subproc
from ddev_studio.ui.dialogs.progress import ProgressDialog
from ddev_studio.ui.helpers import load_icon


class DrupalToolsView(Gtk.Box):
    def __init__(self, main_app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_app = main_app
        self.proj = {}
        self.project_name = ""
        self.approot = ""
        self.docroot = "web"
        self.primary_url = ""
        self.subsite_name = ""
        self.subsite_url = ""
        self.from_view = "list"
        
        self.api_status = {}
        
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(10)
        self.set_margin_bottom(14)
        
        # 0. Top Navigation Bar (Volver + Breadcrumb + Refrescar)
        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        nav_bar.get_style_context().add_class("nav-bar-box")
        
        self.btn_back = Gtk.Button()
        self.btn_back_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_back_icon = Gtk.Image.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.btn_back_lbl = Gtk.Label(label="Volver a Mis Proyectos")
        self.btn_back_box.pack_start(self.btn_back_icon, False, False, 0)
        self.btn_back_box.pack_start(self.btn_back_lbl, False, False, 0)
        self.btn_back.add(self.btn_back_box)
        self.btn_back.get_style_context().add_class("btn-back")
        self.btn_back.connect("clicked", lambda b: self.on_back_clicked())
        nav_bar.pack_start(self.btn_back, False, False, 0)
        
        self.lbl_breadcrumb = Gtk.Label()
        self.lbl_breadcrumb.set_markup("<span color='#94a3b8'>Mis Proyectos / </span><b>Asistente de Código y APIs Drupal</b>")
        self.lbl_breadcrumb.set_halign(Gtk.Align.START)
        nav_bar.pack_start(self.lbl_breadcrumb, True, True, 0)
        
        btn_refresh = Gtk.Button()
        btn_refresh.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        btn_refresh.set_tooltip_text("Refrescar módulos, temas y estado de APIs")
        btn_refresh.connect("clicked", lambda b: self.refresh_view())
        nav_bar.pack_start(btn_refresh, False, False, 0)
        
        self.pack_start(nav_bar, False, False, 0)
        
        # Header Box (Project Summary Card)
        self.header_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.header_card.get_style_context().add_class("option-highlight-box")
        
        self.icon_img = Gtk.Image()
        pix = load_icon("drupal.svg", 44)
        if pix:
            self.icon_img.set_from_pixbuf(pix)
        else:
            self.icon_img.set_from_icon_name("applications-development", Gtk.IconSize.DIALOG)
        self.header_card.pack_start(self.icon_img, False, False, 0)
        
        vbox_txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.lbl_title = Gtk.Label()
        self.lbl_title.set_markup("<span size='large' weight='bold'>Drupal Studio</span>")
        self.lbl_title.set_halign(Gtk.Align.START)
        vbox_txt.pack_start(self.lbl_title, False, False, 0)
        
        self.lbl_sub = Gtk.Label()
        self.lbl_sub.set_markup("<span color='#94a3b8' size='small'>Docroot: <tt>web</tt></span>")
        self.lbl_sub.set_halign(Gtk.Align.START)
        vbox_txt.pack_start(self.lbl_sub, False, False, 0)
        self.header_card.pack_start(vbox_txt, True, True, 0)
        
        self.pack_start(self.header_card, False, False, 0)
        
        # Notebook with Tabs
        self.notebook = Gtk.Notebook()
        self.pack_start(self.notebook, True, True, 0)
        
        # Tab 1: Generador de Código
        tab_scaffold = self.build_tab_scaffolding()
        lbl_scaffold = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_scaffold.pack_start(Gtk.Image.new_from_icon_name("system-run-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_scaffold.pack_start(Gtk.Label(label="Generador de Código"), False, False, 0)
        lbl_scaffold.show_all()
        self.notebook.append_page(tab_scaffold, lbl_scaffold)
        
        # Tab 2: Suite de APIs REST & Headless
        tab_api = self.build_tab_api_suite()
        lbl_api = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_api.pack_start(Gtk.Image.new_from_icon_name("network-wired-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_api.pack_start(Gtk.Label(label="Suite de APIs & Headless"), False, False, 0)
        lbl_api.show_all()
        self.notebook.append_page(tab_api, lbl_api)
        
        # Tab 3: Endpoints Custom (@RestResource)
        tab_endpoints = self.build_tab_endpoints()
        lbl_endpoints = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_endpoints.pack_start(Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_endpoints.pack_start(Gtk.Label(label="Endpoints (@RestResource)"), False, False, 0)
        lbl_endpoints.show_all()
        self.notebook.append_page(tab_endpoints, lbl_endpoints)

    def load_project(self, proj, from_view="list"):
        """
        Carga el proyecto seleccionado y actualiza la vista embebida.
        """
        self.proj = proj or {}
        self.project_name = self.proj.get("name", "")
        self.subsite_name = self.proj.get("subsite_name", "")
        self.subsite_url = self.proj.get("subsite_url", "")
        self.approot = self.proj.get("approot", "")
        cfg = read_ddev_config(self.approot) if self.approot else None
        if cfg and cfg.get("docroot"):
            self.docroot = str(cfg.get("docroot")).strip()
        else:
            self.docroot = self.proj.get("docroot") or ("web" if self.approot and os.path.isdir(os.path.join(self.approot, "web")) else ("docroot" if self.approot and os.path.isdir(os.path.join(self.approot, "docroot")) else "web"))
        self.primary_url = self.subsite_url or f"https://{self.project_name}.ddev.site"
        self.from_view = from_view
        
        # Actualizar botón Volver y breadcrumb según origen
        if self.from_view == "details":
            self.btn_back_lbl.set_text("Volver a Detalles")
            self.lbl_breadcrumb.set_markup(f"<span color='#94a3b8'>Mis Proyectos / {self.project_name} (Detalles) / </span><b>Asistente Drupal</b>")
        elif self.from_view == "subsites":
            self.btn_back_lbl.set_text("Volver a Subsitios")
            sub_lbl = f"Subsitio: {self.subsite_name}" if self.subsite_name else "Multisite"
            self.lbl_breadcrumb.set_markup(f"<span color='#94a3b8'>Mis Proyectos / {self.project_name} / {sub_lbl} / </span><b>Asistente Drupal</b>")
        else:
            self.btn_back_lbl.set_text("Volver a Mis Proyectos")
            self.lbl_breadcrumb.set_markup(f"<span color='#94a3b8'>Mis Proyectos / {self.project_name} / </span><b>Asistente Drupal</b>")
            
        # Actualizar cabecera informativa
        if self.subsite_name:
            self.lbl_title.set_markup(f"<span size='large' weight='bold'>Drupal Studio — {GLib.markup_escape_text(self.project_name)} <span color='#8b5cf6'>({GLib.markup_escape_text(self.subsite_name)})</span></span>")
            self.lbl_sub.set_markup(f"<span color='#94a3b8' size='small'>Subsitio: <b>{GLib.markup_escape_text(self.subsite_name)}</b> | Docroot: <tt>{self.docroot}</tt> | URL: <tt>{self.primary_url}</tt></span>")
        else:
            self.lbl_title.set_markup(f"<span size='large' weight='bold'>Drupal Studio — {GLib.markup_escape_text(self.project_name)}</span>")
            self.lbl_sub.set_markup(f"<span color='#94a3b8' size='small'>Docroot: <tt>{self.docroot}</tt> | URL: <tt>{self.primary_url}</tt></span>")
        
        # Configurar generador de temas según versión de Drupal
        self.ptype = str(self.proj.get("type", "")).lower()
        if "drupal8" in self.ptype:
            self.combo_thm_type.set_active_id("subtheme")
            self.combo_thm_preset.set_active_id("classy")
        elif "drupal7" in self.ptype:
            self.combo_thm_type.set_active_id("subtheme")
            self.combo_thm_preset.set_active_id("bartik")
        else:
            self.combo_thm_type.set_active_id("starterkit")
            self.combo_thm_preset.set_active_id("olivero")
        self.update_preset_ui()
        
        # Refrescar listas de módulos/temas y estado de APIs
        self.refresh_view()

    def on_back_clicked(self):
        """
        Regresa a la vista previa adecuada sin perder contexto.
        """
        if self.from_view == "details":
            self.main_app.open_project_details(self.proj)
        elif self.from_view == "subsites":
            self.main_app.open_subsites_manager(self.proj)
        else:
            self.main_app.show_projects_list()

    def refresh_view(self):
        """
        Refresca componentes dinámicos y estado en segundo plano.
        """
        self.populate_custom_modules()
        self.refresh_api_status()

    def on_theme_scaffold_completed(self):
        """
        Callback ejecutado al finalizar la generación de un tema/subtema.
        """
        self.refresh_view()
        self.update_preset_ui()

    # -------------------------------------------------------------------------
    # TAB 1: GENERADOR DE CÓDIGO (SCAFFOLDING)
    # -------------------------------------------------------------------------
    def build_tab_scaffolding(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        scrolled.add(main_box)
        
        # Selector de Tipo de Generador
        lbl_sec = Gtk.Label()
        lbl_sec.set_markup("<b>1. Selecciona qué deseas generar:</b>")
        lbl_sec.set_halign(Gtk.Align.START)
        main_box.pack_start(lbl_sec, False, False, 0)
        
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_gen_module = Gtk.RadioButton(label="📦 Módulo Personalizado")
        self.btn_gen_module.connect("toggled", self.on_scaffold_mode_changed)
        mode_box.pack_start(self.btn_gen_module, False, False, 0)
        
        self.btn_gen_theme = Gtk.RadioButton(group=self.btn_gen_module, label="🎨 Tema / Subtema (Starterkit)")
        self.btn_gen_theme.connect("toggled", self.on_scaffold_mode_changed)
        mode_box.pack_start(self.btn_gen_theme, False, False, 0)
        
        self.btn_gen_component = Gtk.RadioButton(group=self.btn_gen_module, label="🧩 Componente Interno")
        self.btn_gen_component.connect("toggled", self.on_scaffold_mode_changed)
        mode_box.pack_start(self.btn_gen_component, False, False, 0)
        
        main_box.pack_start(mode_box, False, False, 0)
        
        # Stack con formularios
        self.stack_scaffold = Gtk.Stack()
        self.stack_scaffold.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        
        # Form A: Módulo
        self.stack_scaffold.add_named(self.build_module_form(), "module")
        # Form B: Tema
        self.stack_scaffold.add_named(self.build_theme_form(), "theme")
        # Form C: Componente
        self.stack_scaffold.add_named(self.build_component_form(), "component")
        
        main_box.pack_start(self.stack_scaffold, False, False, 0)
        
        # Acciones de Ejecución
        box_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box_actions.set_halign(Gtk.Align.END)
        box_actions.set_margin_top(10)
        
        btn_terminal = Gtk.Button()
        b_term_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_term_box.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_term_box.pack_start(Gtk.Label(label="Abrir Asistente en Terminal"), False, False, 0)
        btn_terminal.add(b_term_box)
        btn_terminal.set_tooltip_text("Abre la terminal interactiva con 'ddev drush generate'")
        btn_terminal.connect("clicked", self.on_open_interactive_generator)
        box_actions.pack_start(btn_terminal, False, False, 0)
        
        self.btn_run_gen = Gtk.Button()
        self.btn_run_gen.get_style_context().add_class("btn-primary")
        b_run_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_run_box.pack_start(Gtk.Image.new_from_icon_name("system-run-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_run_box.pack_start(Gtk.Label(label="Generar Código"), False, False, 0)
        self.btn_run_gen.add(b_run_box)
        self.btn_run_gen.connect("clicked", self.on_execute_scaffold)
        box_actions.pack_start(self.btn_run_gen, False, False, 0)
        
        main_box.pack_start(box_actions, False, False, 0)
        
        return scrolled

    def build_module_form(self):
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(8)
        
        # Nombre Legible
        lbl1 = Gtk.Label(label="Nombre del Módulo:")
        lbl1.set_halign(Gtk.Align.END)
        grid.attach(lbl1, 0, 0, 1, 1)
        self.entry_mod_name = Gtk.Entry()
        self.entry_mod_name.set_placeholder_text("ej. Mi Funcionalidad, Blog Custom, Pasarela Pagos")
        self.entry_mod_name.set_hexpand(True)
        self.entry_mod_name.connect("changed", self.on_module_name_changed)
        grid.attach(self.entry_mod_name, 1, 0, 1, 1)
        
        # Machine Name
        lbl2 = Gtk.Label(label="Machine Name:")
        lbl2.set_halign(Gtk.Align.END)
        grid.attach(lbl2, 0, 1, 1, 1)
        self.entry_mod_machine = Gtk.Entry()
        self.entry_mod_machine.set_placeholder_text("ej. mi_funcionalidad")
        self.entry_mod_machine.set_hexpand(True)
        grid.attach(self.entry_mod_machine, 1, 1, 1, 1)
        
        # Descripción
        lbl3 = Gtk.Label(label="Descripción:")
        lbl3.set_halign(Gtk.Align.END)
        grid.attach(lbl3, 0, 2, 1, 1)
        self.entry_mod_desc = Gtk.Entry()
        self.entry_mod_desc.set_text("Módulo personalizado para funcionalidades específicas.")
        self.entry_mod_desc.set_hexpand(True)
        grid.attach(self.entry_mod_desc, 1, 2, 1, 1)
        
        # Paquete
        lbl4 = Gtk.Label(label="Paquete:")
        lbl4.set_halign(Gtk.Align.END)
        grid.attach(lbl4, 0, 3, 1, 1)
        self.entry_mod_package = Gtk.Entry()
        self.entry_mod_package.set_text("Custom")
        grid.attach(self.entry_mod_package, 1, 3, 1, 1)
        
        # Checkboxes
        box_checks = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.chk_mod_install = Gtk.CheckButton(label="Generar archivo .install")
        self.chk_mod_install.set_active(True)
        box_checks.pack_start(self.chk_mod_install, False, False, 0)
        
        self.chk_mod_permissions = Gtk.CheckButton(label="Generar .permissions.yml")
        box_checks.pack_start(self.chk_mod_permissions, False, False, 0)
        
        self.chk_mod_libraries = Gtk.CheckButton(label="Generar .libraries.yml")
        box_checks.pack_start(self.chk_mod_libraries, False, False, 0)
        
        grid.attach(box_checks, 1, 4, 1, 1)
        
        return grid

    def build_theme_form(self):
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(8)
        
        # Nombre del Tema
        lbl1 = Gtk.Label(label="Nombre del Tema:")
        lbl1.set_halign(Gtk.Align.END)
        grid.attach(lbl1, 0, 0, 1, 1)
        self.entry_thm_name = Gtk.Entry()
        self.entry_thm_name.set_placeholder_text("ej. Mi Tema Corporativo, Portal Web")
        self.entry_thm_name.set_hexpand(True)
        self.entry_thm_name.connect("changed", self.on_theme_name_changed)
        grid.attach(self.entry_thm_name, 1, 0, 1, 1)
        
        # Machine Name
        lbl2 = Gtk.Label(label="Machine Name:")
        lbl2.set_halign(Gtk.Align.END)
        grid.attach(lbl2, 0, 1, 1, 1)
        self.entry_thm_machine = Gtk.Entry()
        self.entry_thm_machine.set_placeholder_text("ej. mi_tema_corporativo")
        self.entry_thm_machine.set_hexpand(True)
        grid.attach(self.entry_thm_machine, 1, 1, 1, 1)
        
        # Tipo de Generador
        lbl3 = Gtk.Label(label="Generador / Modo:")
        lbl3.set_halign(Gtk.Align.END)
        grid.attach(lbl3, 0, 2, 1, 1)
        self.combo_thm_type = Gtk.ComboBoxText()
        self.combo_thm_type.append("starterkit", "Starterkit Moderno (Drupal 10/11 - Clon Autónomo)")
        self.combo_thm_type.append("subtheme", "Subtema Guiado (Bootstrap 5, Barrio, Radix, Olivero, Gin...)")
        self.combo_thm_type.set_active(0)
        self.combo_thm_type.connect("changed", self.on_thm_type_changed)
        grid.attach(self.combo_thm_type, 1, 2, 1, 1)
        
        # Tema Base (Selector de Preset)
        lbl4 = Gtk.Label(label="Tema Base:")
        lbl4.set_halign(Gtk.Align.END)
        grid.attach(lbl4, 0, 3, 1, 1)
        
        base_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        self.combo_thm_preset = Gtk.ComboBoxText()
        for p_id, p_data in DRUPAL_BASE_THEMES_PRESETS.items():
            self.combo_thm_preset.append(p_id, p_data["label"])
        self.combo_thm_preset.set_active_id("olivero")
        self.combo_thm_preset.connect("changed", self.on_thm_preset_changed)
        base_box.pack_start(self.combo_thm_preset, False, False, 0)
        
        # Entrada manual cuando se elige "custom"
        self.entry_thm_base = Gtk.Entry()
        self.entry_thm_base.set_placeholder_text("Escribe el machine_name del tema base...")
        self.entry_thm_base.set_no_show_all(True)
        self.entry_thm_base.hide()
        base_box.pack_start(self.entry_thm_base, False, False, 0)
        
        # Etiqueta de estado del tema base (disponible vs requiere composer)
        self.lbl_base_status = Gtk.Label()
        self.lbl_base_status.set_xalign(0.0)
        base_box.pack_start(self.lbl_base_status, False, False, 0)
        
        grid.attach(base_box, 1, 3, 1, 1)
        
        # Opciones avanzadas de despliegue
        lbl5 = Gtk.Label(label="Opciones:")
        lbl5.set_halign(Gtk.Align.END)
        grid.attach(lbl5, 0, 4, 1, 1)
        
        opts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        self.chk_thm_install_base = Gtk.CheckButton(label="Descargar e instalar tema base con Composer si falta (ddev composer require)")
        self.chk_thm_install_base.set_active(True)
        opts_box.pack_start(self.chk_thm_install_base, False, False, 0)
        
        self.chk_thm_set_default = Gtk.CheckButton(label="Establecer como tema predeterminado del sitio tras crearlo")
        self.chk_thm_set_default.set_active(True)
        opts_box.pack_start(self.chk_thm_set_default, False, False, 0)
        
        grid.attach(opts_box, 1, 4, 1, 1)
        
        return grid

    def on_thm_type_changed(self, combo):
        is_subtheme = combo.get_active_id() == "subtheme"
        self.combo_thm_preset.set_sensitive(is_subtheme)
        self.chk_thm_install_base.set_sensitive(is_subtheme)
        if not is_subtheme:
            self.lbl_base_status.set_markup("<span color='#94a3b8' size='small'>ℹ Starterkit genera un clon independiente de starterkit_theme</span>")
        else:
            self.update_preset_ui()

    def on_thm_preset_changed(self, combo):
        self.update_preset_ui()

    def update_preset_ui(self):
        preset_id = self.combo_thm_preset.get_active_id() or "olivero"
        preset_info = DRUPAL_BASE_THEMES_PRESETS.get(preset_id, {})
        is_custom = preset_id == "custom"
        
        if is_custom:
            self.entry_thm_base.show()
        else:
            self.entry_thm_base.hide()
            
        base_name = preset_info.get("base_theme", preset_id)
        pkg = preset_info.get("composer_pkg")
        is_admin = preset_info.get("type") == "admin"
        
        # Ajustar label de tema predeterminado
        if is_admin:
            self.chk_thm_set_default.set_label("Establecer como tema de administración predeterminado (system.theme admin)")
        else:
            self.chk_thm_set_default.set_label("Establecer como tema predeterminado del sitio (system.theme default)")
            
        # Comprobar si está instalado
        if is_custom:
            self.lbl_base_status.set_markup("<span color='#94a3b8' size='small'>Escribe el machine_name del tema que servirá de base</span>")
            self.chk_thm_install_base.set_sensitive(False)
        elif preset_info.get("is_core"):
            self.lbl_base_status.set_markup("<span color='#10b981' size='small'>✓ Tema del Core de Drupal (no requiere Composer)</span>")
            self.chk_thm_install_base.set_sensitive(False)
        else:
            installed = is_theme_installed(self.approot, self.docroot, base_name)
            self.chk_thm_install_base.set_sensitive(True)
            if installed:
                self.lbl_base_status.set_markup(f"<span color='#10b981' size='small'>✓ <b>{base_name}</b> ya está instalado en el proyecto</span>")
            else:
                self.lbl_base_status.set_markup(f"<span color='#f59e0b' size='small'>📦 Requiere descargar paquete Composer: <b>{pkg}</b></span>")

    def build_component_form(self):
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(8)
        
        # Tipo de Componente
        lbl1 = Gtk.Label(label="Tipo de Componente:")
        lbl1.set_halign(Gtk.Align.END)
        grid.attach(lbl1, 0, 0, 1, 1)
        
        self.combo_cmp_type = Gtk.ComboBoxText()
        self.combo_cmp_type.append("controller", "Controlador (Controller con Ruta routing.yml)")
        self.combo_cmp_type.append("plugin:block", "Bloque Personalizado (Block Plugin)")
        self.combo_cmp_type.append("service", "Servicio (Service con Inyección de Dependencias)")
        self.combo_cmp_type.append("form:simple", "Formulario Simple (FormBase)")
        self.combo_cmp_type.append("form:config", "Formulario de Configuración (ConfigFormBase)")
        self.combo_cmp_type.append("sdc", "Single Directory Component (SDC)")
        self.combo_cmp_type.append("entity:content", "Entidad de Contenido (Content Entity)")
        self.combo_cmp_type.set_active(0)
        grid.attach(self.combo_cmp_type, 1, 0, 1, 1)
        
        # Módulo Destino
        lbl2 = Gtk.Label(label="Módulo Destino:")
        lbl2.set_halign(Gtk.Align.END)
        grid.attach(lbl2, 0, 1, 1, 1)
        
        box_mod_target = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.combo_cmp_module = Gtk.ComboBoxText()
        self.combo_cmp_module.set_hexpand(True)
        box_mod_target.pack_start(self.combo_cmp_module, True, True, 0)
        
        btn_refresh_mods = Gtk.Button()
        btn_refresh_mods.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        btn_refresh_mods.set_tooltip_text("Refrescar módulos personalizados")
        btn_refresh_mods.connect("clicked", lambda b: self.populate_custom_modules())
        box_mod_target.pack_start(btn_refresh_mods, False, False, 0)
        
        grid.attach(box_mod_target, 1, 1, 1, 1)
        
        # Nombre de Clase / Componente
        lbl3 = Gtk.Label(label="Nombre del Componente:")
        lbl3.set_halign(Gtk.Align.END)
        grid.attach(lbl3, 0, 2, 1, 1)
        self.entry_cmp_name = Gtk.Entry()
        self.entry_cmp_name.set_placeholder_text("ej. DashboardController, UserStatsBlock, WeatherService")
        self.entry_cmp_name.set_hexpand(True)
        grid.attach(self.entry_cmp_name, 1, 2, 1, 1)
        
        return grid

    def populate_custom_modules(self):
        if not hasattr(self, "combo_cmp_module") or not hasattr(self, "combo_ep_module"):
            return
            
        self.combo_cmp_module.remove_all()
        self.combo_ep_module.remove_all()
        
        if not self.approot:
            self.combo_cmp_module.append("none", "No hay proyecto cargado")
            self.combo_cmp_module.set_active(0)
            self.combo_ep_module.append("none", "No hay proyecto cargado")
            self.combo_ep_module.set_active(0)
            return
            
        mods = scan_custom_modules(self.approot, self.docroot)
        if mods:
            for m in mods:
                self.combo_cmp_module.append(m["name"], f"{m['name']} ({m['rel_path']})")
                self.combo_ep_module.append(m["name"], f"{m['name']} ({m['rel_path']})")
            self.combo_cmp_module.set_active(0)
            self.combo_ep_module.set_active(0)
        else:
            self.combo_cmp_module.append("none", "No hay módulos en web/modules/custom (Crea uno primero)")
            self.combo_cmp_module.set_active(0)
            self.combo_ep_module.append("none", "No se detectaron módulos custom en web/modules/custom/")
            self.combo_ep_module.set_active(0)

    def on_scaffold_mode_changed(self, btn):
        if self.btn_gen_module.get_active():
            self.stack_scaffold.set_visible_child_name("module")
        elif self.btn_gen_theme.get_active():
            self.stack_scaffold.set_visible_child_name("theme")
        elif self.btn_gen_component.get_active():
            self.stack_scaffold.set_visible_child_name("component")
            self.populate_custom_modules()

    def on_module_name_changed(self, entry):
        val = entry.get_text()
        self.entry_mod_machine.set_text(sanitize_machine_name(val))

    def on_theme_name_changed(self, entry):
        val = entry.get_text()
        self.entry_thm_machine.set_text(sanitize_machine_name(val))

    def on_open_interactive_generator(self, btn):
        if not self.approot:
            return
        if self.btn_gen_module.get_active():
            gen = "module"
        elif self.btn_gen_theme.get_active():
            gen = "theme"
        else:
            gen = self.combo_cmp_type.get_active_id() or "controller"
            
        uri_flag = f"--uri={self.primary_url} " if self.subsite_url else ""
        open_terminal(self.approot, f"ddev drush {uri_flag}generate {gen}")

    def on_execute_scaffold(self, btn):
        if not self.approot:
            return
            
        if self.btn_gen_module.get_active():
            name = self.entry_mod_name.get_text().strip()
            machine = sanitize_machine_name(self.entry_mod_machine.get_text().strip())
            if not machine:
                return
            desc = self.entry_mod_desc.get_text().strip()
            pkg = self.entry_mod_package.get_text().strip() or "Custom"
            has_install = self.chk_mod_install.get_active()
            has_perm = self.chk_mod_permissions.get_active()
            
            def do_scaffold_module(log):
                log("🔨 Generando estructura de archivos para módulo personalizado...")
                files = scaffold_custom_module(
                    self.approot, self.docroot, machine, name, desc, pkg, has_install, has_perm
                )
                for f in files:
                    log(f"  ✓ Creado: {f}")
            
            cmd = ["ddev", "drush"]
            if self.subsite_url:
                cmd.append(f"--uri={self.subsite_url}")
            cmd.append("cr")
            
            self.run_task_with_progress(
                f"Generando Módulo: {machine}",
                cmd,
                f"Módulo '{machine}' creado exitosamente en web/modules/custom/{machine}",
                pre_action=do_scaffold_module,
                on_complete=self.populate_custom_modules
            )
            
        elif self.btn_gen_theme.get_active():
            machine = sanitize_machine_name(self.entry_thm_machine.get_text().strip())
            name = self.entry_thm_name.get_text().strip() or machine
            if not machine:
                return
            thm_type = self.combo_thm_type.get_active_id()
            preset_id = self.combo_thm_preset.get_active_id() or "olivero"
            preset_info = DRUPAL_BASE_THEMES_PRESETS.get(preset_id, {})
            if preset_id == "custom":
                base = self.entry_thm_base.get_text().strip() or "olivero"
                composer_pkg = None
                is_admin = False
            else:
                base = preset_info.get("base_theme") or preset_id
                composer_pkg = preset_info.get("composer_pkg")
                is_admin = preset_info.get("type") == "admin"

            if thm_type == "starterkit":
                cmd = build_starterkit_theme_command(machine, name, self.docroot, self.subsite_url)
                self.run_task_with_progress(
                    f"Generando Starterkit: {machine}",
                    cmd,
                    f"Tema Starterkit '{machine}' creado exitosamente en {self.docroot}/themes/custom/{machine}",
                    on_complete=self.on_theme_scaffold_completed
                )
            else:
                already_installed = is_theme_installed(self.approot, self.docroot, base)
                need_install = bool(composer_pkg and not already_installed and self.chk_thm_install_base.get_active())
                set_as_default = self.chk_thm_set_default.get_active()
                
                def do_scaffold_theme(log):
                    log(f"🎨 Generando estructura del subtema '{machine}' basado en '{base}'...")
                    files = scaffold_custom_theme(self.approot, self.docroot, machine, name, base)
                    for f in files:
                        log(f"  ✓ Creado: {f}")
                
                cmd = build_subtheme_command(
                    machine_name=machine,
                    base_theme=base,
                    composer_pkg=composer_pkg,
                    install_base=need_install,
                    enable_theme=True,
                    set_as_default=set_as_default,
                    is_admin_theme=is_admin,
                    subsite_url=self.subsite_url
                )
                
                self.run_task_with_progress(
                    f"Generando Subtema: {machine}",
                    cmd,
                    f"Subtema '{machine}' ({base}) configurado exitosamente en {self.docroot}/themes/custom/{machine}",
                    pre_action=do_scaffold_theme,
                    on_complete=self.on_theme_scaffold_completed
                )
            
        elif self.btn_gen_component.get_active():
            cmp_type = self.combo_cmp_type.get_active_id() or "controller"
            target_mod = self.combo_cmp_module.get_active_id()
            uri_flag = f"--uri={self.primary_url} " if self.subsite_url else ""
            if not target_mod or target_mod == "none":
                open_terminal(self.approot, f"ddev drush {uri_flag}generate {cmp_type}")
                return
            cmp_name = self.entry_cmp_name.get_text().strip()
            if not cmp_name:
                open_terminal(self.approot, f"ddev drush {uri_flag}generate {cmp_type}")
                return
                
            def do_scaffold_cmp(log):
                log(f"⚙️ Generando componente '{cmp_type}' ({cmp_name}) en módulo '{target_mod}'...")
                files = scaffold_custom_component(self.approot, self.docroot, target_mod, cmp_type, cmp_name)
                for f in files:
                    log(f"  ✓ Creado: {f}")
            
            cmd = ["ddev", "drush"]
            if self.subsite_url:
                cmd.append(f"--uri={self.subsite_url}")
            cmd.append("cr")
            
            self.run_task_with_progress(
                f"Generando {cmp_type}: {cmp_name}",
                cmd,
                f"Componente '{cmp_name}' generado exitosamente en {target_mod}",
                pre_action=do_scaffold_cmp
            )

    # -------------------------------------------------------------------------
    # TAB 2: SUITE DE MÓDULOS ESENCIALES & APIS
    # -------------------------------------------------------------------------
    def build_tab_api_suite(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        scrolled.add(main_box)
        
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_info = Gtk.Label()
        lbl_info.set_markup("<b>Suite de Módulos Fundamentales y Bundles para Drupal 10/11:</b>")
        top_bar.pack_start(lbl_info, True, True, 0)

        btn_uninstall_page = Gtk.Button()
        btn_un_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_un_box.pack_start(Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        btn_un_box.pack_start(Gtk.Label(label="Desinstalar en Drupal"), False, False, 0)
        btn_uninstall_page.add(btn_un_box)
        btn_uninstall_page.get_style_context().add_class("btn-quick")
        btn_uninstall_page.set_tooltip_text("Abrir la página oficial de desinstalación de Drupal (/admin/modules/uninstall)")
        btn_uninstall_page.connect(
            "clicked",
            lambda b: webbrowser.open(get_drupal_uninstall_url(self.primary_url or f"https://{self.project_name}.ddev.site"))
        )
        top_bar.pack_start(btn_uninstall_page, False, False, 0)

        btn_refresh_api = Gtk.Button()
        btn_refresh_api.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        btn_refresh_api.set_tooltip_text("Actualizar estado de módulos")
        btn_refresh_api.connect("clicked", lambda b: self.refresh_api_status())
        top_bar.pack_start(btn_refresh_api, False, False, 0)
        main_box.pack_start(top_bar, False, False, 0)
        
        # 1. BUNDLE SEO: Metatag, Pathauto, Token, Simple Sitemap, Redirect
        self.card_seo = self.create_bundle_card(
            title="🔍 Suite SEO & Posicionamiento en Buscadores",
            desc="Metatag (OpenGraph + Twitter Cards), Pathauto (URLs limpias), Token, Simple XML Sitemap y Redirects automáticos.",
            status_keys=["token", "pathauto", "metatag", "simple_sitemap", "redirect"],
            btn_install_label="📦 Instalar Suite SEO Completa",
            cmd_install=[
                "ddev", "exec", "bash", "-c",
                "composer require drupal/metatag drupal/pathauto drupal/token drupal/simple_sitemap drupal/redirect --no-interaction && drush pm:enable metatag metatag_open_graph metatag_twitter_cards pathauto token simple_sitemap redirect -y && drush cr"
            ],
            success_msg="¡Suite SEO completa instalada y configurada!",
            extra_actions=[
                ("⚙️ Metatags", lambda: webbrowser.open(f"{self.primary_url}/admin/config/search/metatag")),
                ("🔗 Patrones Pathauto", lambda: webbrowser.open(f"{self.primary_url}/admin/config/search/path/patterns")),
                ("🗺️ Sitemap (/sitemap.xml)", lambda: webbrowser.open(f"{self.primary_url}/sitemap.xml")),
            ],
            modules_meta=[
                ("token", "Token"),
                ("pathauto", "Pathauto"),
                ("metatag", "Metatag"),
                ("simple_sitemap", "Simple Sitemap"),
                ("redirect", "Redirect"),
            ]
        )
        main_box.pack_start(self.card_seo, False, False, 0)
        
        # 2. BUNDLE ARQUITECTURA: Paragraphs, Paragraphs Library, Entity Usage, Field Group, Inline Entity Form
        self.card_paragraphs = self.create_bundle_card(
            title="🧩 Arquitectura Modular & Paragraphs Suite",
            desc="Paragraphs, Paragraphs Library, Entity Usage, Field Group e Inline Entity Form para modelado de páginas por componentes reutilizables y serialización en APIs.",
            status_keys=["paragraphs", "field_group", "entity_usage", "inline_entity_form"],
            btn_install_label="📦 Instalar Paragraphs & Componentes",
            cmd_install=[
                "ddev", "exec", "bash", "-c",
                "composer require drupal/paragraphs drupal/entity_reference_revisions drupal/field_group drupal/inline_entity_form drupal/entity_usage --no-interaction && drush pm:enable paragraphs entity_usage paragraphs_library entity_reference_revisions field_group inline_entity_form -y && drush cr"
            ],
            success_msg="¡Suite de Paragraphs y Componentes instalada!",
            extra_actions=[
                ("🧩 Paragraph Types", lambda: webbrowser.open(f"{self.primary_url}/admin/structure/paragraphs_type")),
                ("📚 Paragraphs Library", lambda: webbrowser.open(f"{self.primary_url}/admin/content/paragraphs-library")),
                ("📊 Entity Usage", lambda: webbrowser.open(f"{self.primary_url}/admin/config/entity-usage")),
            ],
            modules_meta=[
                ("paragraphs", "Paragraphs"),
                ("paragraphs_library", "Paragraphs Library"),
                ("field_group", "Field Group"),
                ("entity_usage", "Entity Usage"),
                ("inline_entity_form", "Inline Entity Form"),
            ]
        )
        main_box.pack_start(self.card_paragraphs, False, False, 0)
        
        # 3. BUNDLE ADMIN & MEDIOS: Admin Toolbar, Focal Point, Crop, SVG Image
        self.card_admin_media = self.create_bundle_card(
            title="⚡ Administración Avanzada & Gestión de Medios (DX / UX)",
            desc="Admin Toolbar (Tools + Search multinivel), Focal Point (recortes inteligentes de imágenes) y soporte nativo para logotipos SVG.",
            status_keys=["admin_toolbar", "focal_point", "crop", "svg_image"],
            btn_install_label="📦 Instalar Admin Toolbar & Medios",
            cmd_install=[
                "ddev", "exec", "bash", "-c",
                "composer require drupal/admin_toolbar drupal/focal_point drupal/crop drupal/svg_image --no-interaction && drush pm:enable admin_toolbar admin_toolbar_tools admin_toolbar_search focal_point crop svg_image -y && drush cr"
            ],
            success_msg="¡Admin Toolbar, Focal Point y SVG Image instalados!",
            extra_actions=[
                ("⚙️ Admin Toolbar", lambda: webbrowser.open(f"{self.primary_url}/admin/config/user-interface/admin-toolbar")),
                ("🎯 Focal Point", lambda: webbrowser.open(f"{self.primary_url}/admin/config/media/crop-widget")),
            ],
            modules_meta=[
                ("admin_toolbar", "Admin Toolbar"),
                ("focal_point", "Focal Point"),
                ("crop", "Crop API"),
                ("svg_image", "SVG Image"),
            ]
        )
        main_box.pack_start(self.card_admin_media, False, False, 0)
        
        # 4. BUNDLE APIS & HEADLESS: JSON:API, JSON:API Extras, Simple OAuth, RestUI, GraphQL
        self.card_api_headless = self.create_bundle_card(
            title="🌐 Suite de APIs REST, JSON:API & Headless (Decoupled)",
            desc="JSON:API (Core), JSON:API Extras (personalización de esquemas), Simple OAuth (tokens JWT para React/Vue/Next.js), REST Core y GraphQL.",
            status_keys=["jsonapi", "jsonapi_extras", "simple_oauth"],
            btn_install_label="📦 Instalar Suite de APIs & OAuth",
            cmd_install=[
                "ddev", "exec", "bash", "-c",
                "composer require drupal/jsonapi_extras drupal/simple_oauth --no-interaction && drush pm:enable jsonapi jsonapi_extras simple_oauth -y && drush cr"
            ],
            success_msg="¡Suite de APIs REST, JSON:API Extras y Simple OAuth instalados!",
            extra_actions=[
                ("🌐 Probar /jsonapi", lambda: webbrowser.open(f"{self.primary_url}/jsonapi")),
                ("⚙️ JSON:API Extras", lambda: webbrowser.open(f"{self.primary_url}/admin/config/services/jsonapi")),
                ("🗝️ Generar Claves RSA", lambda: self.run_task_with_progress(
                    "Generando par de claves RSA para OAuth",
                    ["ddev", "exec", "bash", "-c", "mkdir -p ../oauth_keys && openssl genrsa -out ../oauth_keys/private.key 2048 && openssl rsa -in ../oauth_keys/private.key -pubout -out ../oauth_keys/public.key && chmod 600 ../oauth_keys/private.key"],
                    "Claves RSA generadas en ../oauth_keys/"
                )),
            ],
            modules_meta=[
                ("jsonapi", "JSON:API"),
                ("jsonapi_extras", "JSON:API Extras"),
                ("simple_oauth", "Simple OAuth"),
            ]
        )
        main_box.pack_start(self.card_api_headless, False, False, 0)
        
        # 5. BUNDLE DEPURACIÓN & LOCAL DDEV: Devel, Kint, Consola PHP, Stage File Proxy
        self.card_devel_stage = self.create_bundle_card(
            title="🐞 Depuración, Consola PHP & Rendimiento Local (DDEV)",
            desc="Devel + Kint, Consola PHP interactiva (/devel/php) y Stage File Proxy (descarga de imágenes bajo demanda desde producción).",
            status_keys=["devel", "devel_php", "stage_file_proxy"],
            btn_install_label="📦 Instalar Devel + Stage File Proxy",
            cmd_install=[
                "ddev", "exec", "bash", "-c",
                "composer require --dev drupal/devel drupal/devel_php kint-php/kint drupal/stage_file_proxy --no-interaction && drush pm:enable devel devel_php stage_file_proxy -y && drush cr"
            ],
            success_msg="¡Devel, Kint y Stage File Proxy instalados con éxito!",
            extra_actions=[
                ("⚡ Abrir Consola PHP (/devel/php)", lambda: webbrowser.open(f"{self.primary_url}/devel/php")),
                ("🖼️ Stage File Proxy", lambda: webbrowser.open(f"{self.primary_url}/admin/config/development/stage_file_proxy")),
            ],
            modules_meta=[
                ("devel", "Devel"),
                ("devel_php", "Devel PHP"),
                ("stage_file_proxy", "Stage File Proxy"),
            ]
        )
        main_box.pack_start(self.card_devel_stage, False, False, 0)
        
        return scrolled

    def create_bundle_card(self, title, desc, status_keys, btn_install_label, cmd_install, success_msg, extra_actions=None, modules_meta=None):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("project-card")
        
        # Header row
        h_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_t = Gtk.Label()
        lbl_t.set_markup(f"<b>{GLib.markup_escape_text(title)}</b>")
        lbl_t.set_halign(Gtk.Align.START)
        h_row.pack_start(lbl_t, True, True, 0)
        
        badge = Gtk.Label(label="Verificando...")
        badge.get_style_context().add_class("badge")
        badge.get_style_context().add_class("badge-stopped")
        h_row.pack_start(badge, False, False, 0)
        card.pack_start(h_row, False, False, 0)
        
        # Description
        lbl_d = Gtk.Label(label=desc)
        lbl_d.set_line_wrap(True)
        lbl_d.set_halign(Gtk.Align.START)
        lbl_d.get_style_context().add_class("header-subtitle")
        card.pack_start(lbl_d, False, False, 0)
        
        # Actions row
        act_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        act_row.set_margin_top(4)
        
        btn_install = Gtk.Button(label=btn_install_label)
        btn_install.get_style_context().add_class("btn-quick")
        btn_install.get_style_context().add_class("btn-quick-cache")
        
        def on_install_clicked(b):
            cmds = list(cmd_install)
            if getattr(self, "subsite_url", "") or getattr(self, "subsite_name", ""):
                target_uri = self.primary_url or getattr(self, "subsite_url", "")
                cmds = [
                    c.replace("drush pm:enable", f"drush --uri={target_uri} pm:enable").replace("drush cr", f"drush --uri={target_uri} cr")
                    if isinstance(c, str) else c
                    for c in cmds
                ]
            self.run_task_with_progress(f"Instalando {title}", cmds, success_msg)
            
        btn_install.connect("clicked", on_install_clicked)
        act_row.pack_start(btn_install, False, False, 0)
        
        if extra_actions:
            for act_label, act_cb in extra_actions:
                btn_extra = Gtk.Button(label=act_label)
                btn_extra.get_style_context().add_class("btn-quick")
                btn_extra.connect("clicked", lambda b, cb=act_cb: cb())
                act_row.pack_start(btn_extra, False, False, 0)
                
        card.pack_start(act_row, False, False, 0)
        
        # Active modules uninstall shortcuts (Direct navigation to Drupal web UI row)
        box_active = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_active.set_margin_top(4)
        box_active.set_no_show_all(True)
        box_active.hide()
        
        lbl_active_hdr = Gtk.Label()
        lbl_active_hdr.set_markup("<span size='small' color='#94a3b8'>Módulos activos (clic para abrir desinstalador de Drupal):</span>")
        lbl_active_hdr.set_halign(Gtk.Align.START)
        box_active.pack_start(lbl_active_hdr, False, False, 0)
        
        flow_active = Gtk.FlowBox()
        flow_active.set_valign(Gtk.Align.START)
        flow_active.set_max_children_per_line(15)
        flow_active.set_selection_mode(Gtk.SelectionMode.NONE)
        flow_active.set_homogeneous(False)
        flow_active.set_row_spacing(4)
        flow_active.set_column_spacing(6)
        box_active.pack_start(flow_active, False, False, 0)
        
        card.pack_start(box_active, False, False, 0)
        
        # Store references
        card._status_badge = badge
        card._status_keys = status_keys
        card._modules_meta = modules_meta or []
        card._box_active = box_active
        card._flow_active = flow_active
        return card

    def refresh_api_status(self):
        if not self.approot:
            return
            
        def task():
            uri = self.primary_url if self.subsite_url else ""
            status = check_drupal_api_status(self.approot, uri=uri)
            GLib.idle_add(self.update_api_status_ui, status)
        threading.Thread(target=task, daemon=True).start()

    def update_api_status_ui(self, status):
        self.api_status = status or {}
        cards = [self.card_seo, self.card_paragraphs, self.card_admin_media, self.card_api_headless, self.card_devel_stage]
        for c in cards:
            keys = getattr(c, "_status_keys", [])
            active_count = sum(1 for k in keys if self.api_status.get(k, False))
            badge = c._status_badge
            ctx = badge.get_style_context()
            ctx.remove_class("badge-running")
            ctx.remove_class("badge-stopped")
            ctx.remove_class("badge-paused")
            
            if active_count == len(keys) and active_count > 0:
                badge.set_text("ACTIVO")
                ctx.add_class("badge-running")
            elif active_count > 0:
                badge.set_text(f"PARCIAL ({active_count}/{len(keys)})")
                ctx.add_class("badge-paused")
            else:
                badge.set_text("INACTIVO")
                ctx.add_class("badge-stopped")
                
            # Actualizar accesos directos de desinstalación para módulos activos
            box_active = getattr(c, "_box_active", None)
            flow_active = getattr(c, "_flow_active", None)
            modules_meta = getattr(c, "_modules_meta", [])
            
            if box_active and flow_active and modules_meta:
                for child in flow_active.get_children():
                    flow_active.remove(child)
                    
                has_active = False
                for mod_machine, mod_label in modules_meta:
                    if self.api_status.get(mod_machine, False):
                        has_active = True
                        btn_un = Gtk.Button()
                        btn_un.get_style_context().add_class("btn-quick")
                        btn_un.get_style_context().add_class("btn-quick-uninstall")
                        
                        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                        icon = Gtk.Image.new_from_icon_name("application-x-addon-symbolic", Gtk.IconSize.BUTTON)
                        lbl = Gtk.Label(label=f"🌐 Desinstalar {mod_label}")
                        btn_box.pack_start(icon, False, False, 0)
                        btn_box.pack_start(lbl, False, False, 0)
                        btn_un.add(btn_box)
                        
                        anchor = get_drupal_uninstall_anchor(mod_machine)
                        btn_un.set_tooltip_text(
                            f"Abrir Drupal en /admin/modules/uninstall#{anchor}\n"
                            f"Te posiciona directamente en la fila de '{mod_label}' para desinstalar de forma segura desde la web."
                        )
                        
                        def make_cb(machine):
                            return lambda b: webbrowser.open(
                                get_drupal_uninstall_url(
                                    self.primary_url or f"https://{self.project_name}.ddev.site",
                                    machine
                                )
                            )
                        btn_un.connect("clicked", make_cb(mod_machine))
                        flow_active.add(btn_un)
                        
                if has_active:
                    box_active.show_all()
                else:
                    box_active.hide()

    # -------------------------------------------------------------------------
    # TAB 3: ENDPOINTS PERSONALIZADOS (@RestResource)
    # -------------------------------------------------------------------------
    def build_tab_endpoints(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        scrolled.add(main_box)
        
        lbl_head = Gtk.Label()
        lbl_head.set_markup("<b>Asistente de Creación de Endpoints REST Personalizados (@RestResource):</b>")
        lbl_head.set_halign(Gtk.Align.START)
        main_box.pack_start(lbl_head, False, False, 0)
        
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)
        
        # Módulo Destino
        lbl1 = Gtk.Label(label="Módulo Destino:")
        lbl1.set_halign(Gtk.Align.END)
        grid.attach(lbl1, 0, 0, 1, 1)
        
        self.combo_ep_module = Gtk.ComboBoxText()
        self.combo_ep_module.set_hexpand(True)
        grid.attach(self.combo_ep_module, 1, 0, 1, 1)
        
        # Plugin ID
        lbl2 = Gtk.Label(label="ID del Plugin REST:")
        lbl2.set_halign(Gtk.Align.END)
        grid.attach(lbl2, 0, 1, 1, 1)
        self.entry_ep_id = Gtk.Entry()
        self.entry_ep_id.set_placeholder_text("ej. custom_data_resource")
        grid.attach(self.entry_ep_id, 1, 1, 1, 1)
        
        # Nombre Legible
        lbl3 = Gtk.Label(label="Nombre Legible:")
        lbl3.set_halign(Gtk.Align.END)
        grid.attach(lbl3, 0, 2, 1, 1)
        self.entry_ep_label = Gtk.Entry()
        self.entry_ep_label.set_placeholder_text("ej. Custom Data Resource")
        grid.attach(self.entry_ep_label, 1, 2, 1, 1)
        
        # Canonical URI
        lbl4 = Gtk.Label(label="Ruta URI Canónica:")
        lbl4.set_halign(Gtk.Align.END)
        grid.attach(lbl4, 0, 3, 1, 1)
        self.entry_ep_uri = Gtk.Entry()
        self.entry_ep_uri.set_text("/api/v1/custom-data")
        grid.attach(self.entry_ep_uri, 1, 3, 1, 1)
        
        # Métodos HTTP
        lbl5 = Gtk.Label(label="Métodos:")
        lbl5.set_halign(Gtk.Align.END)
        grid.attach(lbl5, 0, 4, 1, 1)
        
        box_methods = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.chk_m_get = Gtk.CheckButton(label="GET")
        self.chk_m_get.set_active(True)
        box_methods.pack_start(self.chk_m_get, False, False, 0)
        self.chk_m_post = Gtk.CheckButton(label="POST")
        self.chk_m_post.set_active(True)
        box_methods.pack_start(self.chk_m_post, False, False, 0)
        self.chk_m_patch = Gtk.CheckButton(label="PATCH")
        box_methods.pack_start(self.chk_m_patch, False, False, 0)
        self.chk_m_delete = Gtk.CheckButton(label="DELETE")
        box_methods.pack_start(self.chk_m_delete, False, False, 0)
        grid.attach(box_methods, 1, 4, 1, 1)
        
        main_box.pack_start(grid, False, False, 0)
        
        # Action Buttons
        box_ep_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box_ep_actions.set_halign(Gtk.Align.END)
        box_ep_actions.set_margin_top(10)
        
        btn_ep_term = Gtk.Button()
        b_term_b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_term_b.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_term_b.pack_start(Gtk.Label(label="Generar en Terminal Interactiva"), False, False, 0)
        btn_ep_term.add(b_term_b)
        btn_ep_term.connect("clicked", lambda b: open_terminal(self.approot, "ddev drush generate plugin:rest-resource"))
        box_ep_actions.pack_start(btn_ep_term, False, False, 0)
        
        btn_ep_run = Gtk.Button()
        btn_ep_run.get_style_context().add_class("btn-primary")
        b_run_b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_run_b.pack_start(Gtk.Image.new_from_icon_name("system-run-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_run_b.pack_start(Gtk.Label(label="Generar Plugin REST"), False, False, 0)
        btn_ep_run.add(b_run_b)
        btn_ep_run.connect("clicked", self.on_execute_endpoint_scaffold)
        box_ep_actions.pack_start(btn_ep_run, False, False, 0)
        
        main_box.pack_start(box_ep_actions, False, False, 0)
        return scrolled

    def on_execute_endpoint_scaffold(self, btn):
        if not self.approot:
            return
            
        target_mod = self.combo_ep_module.get_active_id()
        ep_id = sanitize_machine_name(self.entry_ep_id.get_text().strip() or "custom_api_resource")
        label = self.entry_ep_label.get_text().strip() or ep_id
        uri = self.entry_ep_uri.get_text().strip() or "/api/v1/data"
        
        uri_flag = f"--uri={self.primary_url} " if self.subsite_url else ""
        if not target_mod or target_mod == "none":
            open_terminal(self.approot, f"ddev drush {uri_flag}generate plugin:rest-resource")
            return
            
        def do_scaffold_ep(log):
            log(f"🌐 Generando Plugin REST Resource '{ep_id}' en módulo '{target_mod}'...")
            files = scaffold_rest_resource(self.approot, self.docroot, target_mod, ep_id, label, uri)
            for f in files:
                log(f"  ✓ Creado: {f}")
        
        cmd = ["ddev", "drush"]
        if self.subsite_url:
            cmd.append(f"--uri={self.subsite_url}")
        cmd.append("cr")
        
        self.run_task_with_progress(
            f"Generando Plugin REST: {ep_id}",
            cmd,
            f"Plugin REST '{ep_id}' generado en {target_mod}",
            pre_action=do_scaffold_ep
        )

    # -------------------------------------------------------------------------
    # Progress Dialog Runner Helper
    # -------------------------------------------------------------------------
    def run_task_with_progress(self, title, cmd_list, success_msg, pre_action=None, on_complete=None):
        dialog = ProgressDialog(self.main_app, title=title)
        dialog.set_status(f"Ejecutando: {' '.join(cmd_list[:3])}...")
        dialog.present()
        
        def run_thread():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t + "\n")
                log(f"📁 Directorio: {self.approot}")
                
                if pre_action:
                    pre_action(log)
                    log("-" * 50)

                if cmd_list:
                    log(f"$ {' '.join(cmd_list)}\n" + "="*50)
                    run_subproc(cmd_list, self.approot, dialog)
                
                log("\n" + "="*50)
                log("✓ ¡Operación completada con éxito!")
                GLib.idle_add(dialog.finish, True, success_msg, self.primary_url, self.approot)
                GLib.idle_add(self.refresh_api_status)
                GLib.idle_add(self.populate_custom_modules)
                if on_complete:
                    GLib.idle_add(on_complete)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {str(ex)}", "", self.approot)
                
        threading.Thread(target=run_thread, daemon=True).start()
