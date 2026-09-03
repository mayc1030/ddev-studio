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
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from ddev_studio.constants import (
    DEFAULT_SITES_DIR,
    CUSTOM_CSS,
    TECH_CATEGORIES
)
from ddev_studio.core.detector import inspect_project_stack, sanitize_project_name
from ddev_studio.logger import logger
from ddev_studio.core.process import run_subproc
from ddev_studio.core.terminal import open_terminal

from ddev_studio.ui.dialogs.progress import ProgressDialog
from ddev_studio.ui.helpers import load_icon, create_icon_menu_item
from ddev_studio.ui.views.details import ProjectDetailsView
from ddev_studio.ui.views.subsites import SubsitesManagerView
from ddev_studio.ui.views.drupal_tools import DrupalToolsView
from ddev_studio.ui.views.addons import AddonsMarketplaceView
from ddev_studio.ui.views.docker_monitor import DockerMonitorView
from ddev_studio.ui.views.tools import GlobalToolsView
from ddev_studio.ui.views.new_project import NewProjectView



class DDEVManagerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="DDEV Studio")
        self.set_default_size(960, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        ddev_icon = load_icon("ddev.svg", 64)
        if ddev_icon:
            self.set_icon(ddev_icon)
            
        self.active_category = "all"
        self.combo_tech_filter_handler_id = None
        
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_data(CUSTOM_CSS.encode("utf-8") if isinstance(CUSTOM_CSS, str) else CUSTOM_CSS)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as ex:
            logger.warning(f"No se pudo cargar el CSS personalizado: {ex}")

        
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
        
        self.tab_new = NewProjectView(self)
        lbl_new = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_new.pack_start(Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_new.pack_start(Gtk.Label(label="Nuevo Proyecto"), False, False, 0)
        lbl_new.show_all()
        self.notebook.append_page(self.tab_new, lbl_new)
        
        self.tab_tools = GlobalToolsView(self)
        lbl_tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_tools.pack_start(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_tools.pack_start(Gtk.Label(label="Herramientas"), False, False, 0)
        lbl_tools.show_all()
        self.notebook.append_page(self.tab_tools, lbl_tools)

        
        self.tab_addons = AddonsMarketplaceView(self)
        lbl_addons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_addons.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_addons.pack_start(Gtk.Label(label="Add-ons"), False, False, 0)
        lbl_addons.show_all()
        self.notebook.append_page(self.tab_addons, lbl_addons)
        
        self.notebook.connect("switch-page", self.on_notebook_page_switched)

    def on_notebook_page_switched(self, notebook, page, page_num):
        if hasattr(self, "docker_monitor_view"):
            if page_num == 2:
                self.docker_monitor_view.resume_polling()
            else:
                self.docker_monitor_view.pause_polling()

    def switch_to_new_project_tab(self, mode="create"):
        self.notebook.set_current_page(1)
        self.tab_new.switch_mode(mode)

    @property
    def flowbox_fw(self):
        return self.tab_new.flowbox_fw

    @property
    def combo_import_type(self):
        return self.tab_new.combo_import_type

    def on_framework_selected(self, flowbox, child):
        return self.tab_new.on_framework_selected(flowbox, child)

    def on_import_type_changed(self, combo):
        return self.tab_new.on_import_type_changed(combo)

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
        
        # Selector desplegable con soporte de iconos SVG reales desde icons/
        self.tech_filter_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        self.combo_tech_filter = Gtk.ComboBox(model=self.tech_filter_store)
        self.combo_tech_filter.get_style_context().add_class("combo-filter")
        self.combo_tech_filter.set_tooltip_text("Filtrar proyectos por tecnología")
        
        renderer_pix = Gtk.CellRendererPixbuf()
        renderer_pix.set_property("xpad", 4)
        self.combo_tech_filter.pack_start(renderer_pix, False)
        self.combo_tech_filter.add_attribute(renderer_pix, "pixbuf", 0)
        
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_property("xpad", 4)
        self.combo_tech_filter.pack_start(renderer_text, True)
        self.combo_tech_filter.add_attribute(renderer_text, "text", 1)
        self.combo_tech_filter.set_id_column(2)
        
        self.combo_tech_filter_handler_id = self.combo_tech_filter.connect("changed", self.on_tech_filter_changed)
        search_box.pack_start(self.combo_tech_filter, False, False, 0)
        
        btn_import_shortcut = Gtk.Button(label="📁 Importar Carpeta...")
        btn_import_shortcut.set_tooltip_text("Vincular un proyecto o repositorio existente en tu disco a DDEV")
        btn_import_shortcut.connect("clicked", lambda b: self.switch_to_new_project_tab("import"))
        search_box.pack_start(btn_import_shortcut, False, False, 0)
        
        btn_new_shortcut = Gtk.Button(label="➕ Nuevo...")
        btn_new_shortcut.set_tooltip_text("Crear un nuevo proyecto desde cero")
        btn_new_shortcut.connect("clicked", lambda b: self.switch_to_new_project_tab("create"))
        search_box.pack_start(btn_new_shortcut, False, False, 0)
        
        self.box_projects_list_view.pack_start(search_box, False, False, 0)
        
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
        
        # View 4: Drupal Tools Embedded View
        self.drupal_tools_view = DrupalToolsView(self)
        self.stack_projects_tab.add_named(self.drupal_tools_view, "drupal_tools")
        
        # Asegurar que la vista inicial sea siempre la lista de proyectos
        self.stack_projects_tab.set_visible_child_name("list")
        
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
            except subprocess.TimeoutExpired:
                logger.warning("Timeout consultando proyectos DDEV (ddev list -j excedió los 15s)")
                projects = []
            except Exception as ex:
                logger.warning(f"Error al consultar proyectos DDEV (ddev list -j): {ex}")
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
        if hasattr(self, "combo_tech_filter"):
            if self.combo_tech_filter_handler_id:
                self.combo_tech_filter.handler_block(self.combo_tech_filter_handler_id)
            self.combo_tech_filter.set_active_id(cat_id)
            if self.combo_tech_filter_handler_id:
                self.combo_tech_filter.handler_unblock(self.combo_tech_filter_handler_id)
        self.apply_project_filters()

    def on_tech_filter_changed(self, combo):
        active_id = combo.get_active_id()
        if active_id:
            self.active_category = active_id
            self.apply_project_filters()

    def update_projects_ui(self, projects):
        for child in self.projects_list_box.get_children():
            self.projects_list_box.remove(child)
            
        self.lbl_proj_title.set_text(f"Mis Proyectos ({len(projects)})")
        
        if hasattr(self, "tab_addons"):
            self.tab_addons.update_projects(projects)
        if hasattr(self, "docker_monitor_view"):
            self.docker_monitor_view.update_projects(projects)
        
        # Calcular conteos por categoría de tecnología
        cat_counts = {"all": len(projects)}
        for p in projects:
            approot = p.get("approot", "")
            tech_type, _, _, _, _, _ = inspect_project_stack(approot, p, p)
            p["_tech_type"] = tech_type
            cat_id = self.determine_project_category(p, tech_type)
            p["_tech_family"] = cat_id
            cat_counts[cat_id] = cat_counts.get(cat_id, 0) + 1
            
        # Reconstruir opciones del desplegable con iconos SVG reales desde icons/
        if hasattr(self, "combo_tech_filter") and hasattr(self, "tech_filter_store"):
            if self.combo_tech_filter_handler_id:
                self.combo_tech_filter.handler_block(self.combo_tech_filter_handler_id)
                
            self.tech_filter_store.clear()
            
            if projects:
                self.combo_tech_filter.show()
                for cat in TECH_CATEGORIES:
                    cat_id = cat["id"]
                    count = cat_counts.get(cat_id, 0)
                    if cat_id != "all" and count == 0:
                        continue
                        
                    icon_name = cat.get("icon", "ddev.svg")
                    pixbuf = load_icon(icon_name, 18)
                    
                    if cat_id == "all":
                        label = f"Todos los tipos ({count})"
                    else:
                        label = f"{cat['name']} ({count})"
                        
                    self.tech_filter_store.append([pixbuf, label, cat_id])
                    
                if self.active_category != "all" and cat_counts.get(self.active_category, 0) == 0:
                    self.active_category = "all"
                    
                self.combo_tech_filter.set_active_id(self.active_category or "all")
            else:
                self.combo_tech_filter.hide()
                
            if self.combo_tech_filter_handler_id:
                self.combo_tech_filter.handler_unblock(self.combo_tech_filter_handler_id)
                
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
            drush_menu.append(create_icon_menu_item("system-run-symbolic", "🛠️ Asistente de Código y APIs Drupal...", lambda w, pr=proj: self.open_drupal_tools(pr, from_view="list")))
            drush_menu.append(Gtk.SeparatorMenuItem())
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

    def on_global_poweroff(self, widget=None):
        return self.tab_tools.on_global_poweroff(widget)

    def on_global_start_all(self, widget=None):
        return self.tab_tools.on_global_start_all(widget)

    def on_clean_ddev(self, widget=None):
        return self.tab_tools.on_clean_ddev(widget)


    def open_subsites_manager(self, proj):
        self.subsites_manager_view.load_project(proj)
        self.stack_projects_tab.set_visible_child_name("subsites")

    def open_drupal_tools(self, proj, from_view="list"):
        self.drupal_tools_view.load_project(proj, from_view=from_view)
        self.stack_projects_tab.set_visible_child_name("drupal_tools")

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



    def run_subproc(self, cmd, cwd, dialog):
        return run_subproc(cmd, cwd, dialog)
