# -*- coding: utf-8 -*-
"""
Vista de Catálogo Visual de Add-ons de DDEV (Marketplace con 1 Clic).
Permite explorar, buscar, filtrar, paginar, instalar y desinstalar extensiones oficiales y comunitarias.
"""

import threading
import webbrowser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ddev_studio.core.addons import (
    ADDON_CATEGORIES,
    fetch_available_addons,
    get_installed_addons,
    is_addon_installed,
    build_install_addon_command,
    build_remove_addon_command
)
from ddev_studio.core.process import run_subproc
from ddev_studio.ui.dialogs.progress import ProgressDialog


class AddonsMarketplaceView(Gtk.Box):
    def __init__(self, main_app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_app = main_app
        
        self.all_addons = []
        self.projects = []
        self.current_project = None
        self.installed_addons = []
        
        self.active_category = "all"
        self.search_query = ""
        
        # Paginación
        self.current_page = 1
        self.items_per_page = 9
        self.total_pages = 1
        
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        
        self.build_ui()
        
        # Cargar catálogo en segundo plano
        GLib.idle_add(self.load_addons_catalog)

    def build_ui(self):
        # 1. Header & Control Bar Box
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        header_box.get_style_context().add_class("marketplace-header-box")
        
        # Fila 1: Título y botón refrescar
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span size='x-large' weight='bold'>🧩 Catálogo de Add-ons de DDEV</span>")
        lbl_title.set_halign(Gtk.Align.START)
        title_box.pack_start(lbl_title, False, False, 0)
        
        lbl_sub = Gtk.Label()
        lbl_sub.set_markup("<span color='#94a3b8' size='small'>Explora qué hace cada servicio e instálalo en tu proyecto con 1 solo clic.</span>")
        lbl_sub.set_halign(Gtk.Align.START)
        title_box.pack_start(lbl_sub, False, False, 0)
        top_row.pack_start(title_box, True, True, 0)
        
        btn_refresh = Gtk.Button()
        btn_refresh.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        btn_refresh.set_tooltip_text("Refrescar catálogo y estado de add-ons")
        btn_refresh.connect("clicked", lambda b: self.load_addons_catalog(force_refresh=True))
        top_row.pack_start(btn_refresh, False, False, 0)
        header_box.pack_start(top_row, False, False, 0)
        
        # Fila 2: Filtros, selector de proyecto y buscador
        controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        # Selector de Proyecto Destino
        lbl_proj = Gtk.Label(label="Proyecto:")
        lbl_proj.set_halign(Gtk.Align.START)
        controls_row.pack_start(lbl_proj, False, False, 0)
        
        self.combo_project = Gtk.ComboBoxText()
        self.combo_project.set_size_request(220, -1)
        self.combo_project.connect("changed", self.on_project_changed)
        controls_row.pack_start(self.combo_project, False, False, 0)
        
        # Selector de Categoría
        lbl_cat = Gtk.Label(label="Categoría:")
        controls_row.pack_start(lbl_cat, False, False, 0)
        
        self.combo_category = Gtk.ComboBoxText()
        for cat in ADDON_CATEGORIES:
            self.combo_category.append(cat["id"], cat["label"])
        self.combo_category.set_active_id("all")
        self.combo_category.connect("changed", self.on_category_changed)
        controls_row.pack_start(self.combo_category, False, False, 0)
        
        # Buscador en tiempo real
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar add-on (ej: redis, solr, cron)...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        controls_row.pack_start(self.search_entry, True, True, 0)
        
        header_box.pack_start(controls_row, False, False, 0)
        self.pack_start(header_box, False, False, 0)
        
        # 2. Barra de estado / resumen
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_summary = Gtk.Label()
        self.lbl_summary.set_markup("<span size='small' color='#94a3b8'>Cargando catálogo de add-ons...</span>")
        self.lbl_summary.set_halign(Gtk.Align.START)
        status_bar.pack_start(self.lbl_summary, True, True, 0)
        self.pack_start(status_bar, False, False, 0)
        
        # 3. Contenedor de contenido scrollable
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_vexpand(True)
        self.pack_start(self.scrolled, True, True, 0)
        
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.scrolled.add(self.content_stack)
        
        # Vista 1: Loader
        self.loader_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.loader_box.set_halign(Gtk.Align.CENTER)
        self.loader_box.set_valign(Gtk.Align.CENTER)
        self.loader_box.set_margin_top(60)
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(40, 40)
        self.spinner.start()
        self.loader_box.pack_start(self.spinner, False, False, 0)
        
        lbl_loading = Gtk.Label()
        lbl_loading.set_markup("<span size='medium' weight='600'>Consultando catálogo de DDEV Add-ons...</span>")
        self.loader_box.pack_start(lbl_loading, False, False, 0)
        self.content_stack.add_named(self.loader_box, "loading")
        
        # Vista 2: FlowBox de tarjetas
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_column_spacing(14)
        self.flowbox.set_row_spacing(14)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_margin_bottom(12)
        self.content_stack.add_named(self.flowbox, "catalog")
        
        # Vista 3: Estado vacío (sin resultados)
        self.empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.empty_box.set_halign(Gtk.Align.CENTER)
        self.empty_box.set_valign(Gtk.Align.CENTER)
        self.empty_box.set_margin_top(60)
        img_empty = Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.DIALOG)
        self.empty_box.pack_start(img_empty, False, False, 0)
        self.lbl_empty = Gtk.Label()
        self.lbl_empty.set_markup("<span size='medium' weight='600'>No se encontraron add-ons para el filtro aplicado</span>")
        self.empty_box.pack_start(self.lbl_empty, False, False, 0)
        self.content_stack.add_named(self.empty_box, "empty")
        
        self.content_stack.set_visible_child_name("loading")

        # 4. Barra inferior de Paginación
        self.pagination_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pagination_bar.get_style_context().add_class("marketplace-header-box")
        self.pagination_bar.set_margin_top(4)
        
        self.lbl_page_info = Gtk.Label()
        self.lbl_page_info.set_halign(Gtk.Align.START)
        self.lbl_page_info.set_markup("<span size='small' color='#94a3b8'>Página 1 de 1</span>")
        self.pagination_bar.pack_start(self.lbl_page_info, True, True, 0)
        
        btn_nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        
        self.btn_first = Gtk.Button()
        self.btn_first.add(Gtk.Image.new_from_icon_name("go-first-symbolic", Gtk.IconSize.BUTTON))
        self.btn_first.set_tooltip_text("Primera página")
        self.btn_first.connect("clicked", lambda b: self.go_to_page(1))
        btn_nav_box.pack_start(self.btn_first, False, False, 0)
        
        self.btn_prev = Gtk.Button()
        self.btn_prev.add(Gtk.Image.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON))
        self.btn_prev.set_tooltip_text("Página anterior")
        self.btn_prev.connect("clicked", lambda b: self.go_to_page(self.current_page - 1))
        btn_nav_box.pack_start(self.btn_prev, False, False, 0)
        
        self.lbl_current_page_badge = Gtk.Label()
        self.lbl_current_page_badge.get_style_context().add_class("badge")
        self.lbl_current_page_badge.get_style_context().add_class("badge-tech")
        self.lbl_current_page_badge.set_markup("<b>1 / 1</b>")
        btn_nav_box.pack_start(self.lbl_current_page_badge, False, False, 4)
        
        self.btn_next = Gtk.Button()
        self.btn_next.add(Gtk.Image.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON))
        self.btn_next.set_tooltip_text("Página siguiente")
        self.btn_next.connect("clicked", lambda b: self.go_to_page(self.current_page + 1))
        btn_nav_box.pack_start(self.btn_next, False, False, 0)
        
        self.btn_last = Gtk.Button()
        self.btn_last.add(Gtk.Image.new_from_icon_name("go-last-symbolic", Gtk.IconSize.BUTTON))
        self.btn_last.set_tooltip_text("Última página")
        self.btn_last.connect("clicked", lambda b: self.go_to_page(self.total_pages))
        btn_nav_box.pack_start(self.btn_last, False, False, 0)
        
        self.pagination_bar.pack_start(btn_nav_box, False, False, 0)
        
        # Selector de elementos por página
        items_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_per_page = Gtk.Label(label="Por página:")
        lbl_per_page.get_style_context().add_class("header-subtitle")
        items_box.pack_start(lbl_per_page, False, False, 0)
        
        self.combo_per_page = Gtk.ComboBoxText()
        for count in ["6", "9", "12", "18", "24"]:
            self.combo_per_page.append(count, count)
        self.combo_per_page.set_active_id("9")
        self.combo_per_page.connect("changed", self.on_per_page_changed)
        items_box.pack_start(self.combo_per_page, False, False, 0)
        
        self.pagination_bar.pack_end(items_box, False, False, 0)
        self.pack_start(self.pagination_bar, False, False, 0)

    # -------------------------------------------------------------------------
    # Sincronización de Proyectos
    # -------------------------------------------------------------------------
    def update_projects(self, projects):
        """
        Actualiza el selector superior con la lista de proyectos cargados en la ventana principal.
        """
        self.projects = projects or []
        current_id = self.combo_project.get_active_id()
        
        self.combo_project.remove_all()
        
        if not self.projects:
            self.combo_project.append("none", "No hay proyectos detectados")
            self.combo_project.set_active(0)
            self.current_project = None
            self.installed_addons = []
            self.render_catalog()
            return
            
        active_idx = 0
        for i, p in enumerate(self.projects):
            pname = p.get("name", "")
            status = p.get("status", "")
            status_tag = "● " if status == "running" else "○ "
            label = f"{status_tag}{pname}"
            self.combo_project.append(pname, label)
            if current_id and pname == current_id:
                active_idx = i
                
        self.combo_project.set_active(active_idx)

    def on_project_changed(self, combo):
        active_name = combo.get_active_id()
        if not active_name or active_name == "none":
            self.current_project = None
            self.installed_addons = []
            self.render_catalog()
            return
            
        for p in self.projects:
            if p.get("name") == active_name:
                self.current_project = p
                break
                
        self.refresh_installed_for_current_project()

    def refresh_installed_for_current_project(self):
        if not self.current_project:
            self.installed_addons = []
            self.render_catalog()
            return
            
        approot = self.current_project.get("approot", "")
        
        def run_detect():
            installed = get_installed_addons(approot)
            def update_ui():
                self.installed_addons = installed
                self.render_catalog()
            GLib.idle_add(update_ui)
            
        threading.Thread(target=run_detect, daemon=True).start()

    # -------------------------------------------------------------------------
    # Carga y Filtrado del Catálogo
    # -------------------------------------------------------------------------
    def load_addons_catalog(self, force_refresh=False):
        self.content_stack.set_visible_child_name("loading")
        
        def fetch_task():
            addons = fetch_available_addons()
            def on_done():
                self.all_addons = addons
                if self.current_project:
                    self.refresh_installed_for_current_project()
                else:
                    self.render_catalog()
            GLib.idle_add(on_done)
            
        threading.Thread(target=fetch_task, daemon=True).start()

    def on_category_changed(self, combo):
        active_id = combo.get_active_id()
        if active_id:
            self.active_category = active_id
            self.current_page = 1
            self.render_catalog()

    def on_search_changed(self, entry):
        self.search_query = entry.get_text().strip().lower()
        self.current_page = 1
        self.render_catalog()

    def on_per_page_changed(self, combo):
        val = combo.get_active_id()
        if val:
            try:
                self.items_per_page = int(val)
                self.current_page = 1
                self.render_catalog()
            except ValueError:
                pass

    def go_to_page(self, page_num):
        if 1 <= page_num <= self.total_pages and page_num != self.current_page:
            self.current_page = page_num
            self.render_catalog()
            # Scroll al inicio suavemente
            adj = self.scrolled.get_vadjustment()
            if adj:
                adj.set_value(0)

    def get_filtered_addons(self):
        filtered = []
        for a in self.all_addons:
            # 1. Filtro por categoría
            if self.active_category == "official" and a["type"] != "official":
                continue
            elif self.active_category == "contrib" and a["type"] != "contrib":
                continue
            elif self.active_category == "installed":
                if not is_addon_installed(a["title"], self.installed_addons):
                    continue
            elif self.active_category not in ["all", "official", "contrib", "installed"]:
                if a.get("category") != self.active_category:
                    continue
                    
            # 2. Filtro por búsqueda de texto
            if self.search_query:
                text_corpus = f"{a['title']} {a.get('description', '')} {a.get('category', '')}".lower()
                if self.search_query not in text_corpus:
                    continue
                    
            filtered.append(a)
            
        return filtered

    # -------------------------------------------------------------------------
    # Renderizado de Tarjetas de Add-on con Paginación
    # -------------------------------------------------------------------------
    def render_catalog(self):
        for child in self.flowbox.get_children():
            self.flowbox.remove(child)
            
        filtered = self.get_filtered_addons()
        total_items = len(filtered)
        pname = self.current_project.get("name", "Ninguno") if self.current_project else "Ninguno"
        
        # Calcular paginación
        self.total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        if self.current_page < 1:
            self.current_page = 1
            
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)
        page_items = filtered[start_idx:end_idx]
        
        # Actualizar resumen superior
        num_installed = len(self.installed_addons) if self.current_project else 0
        self.lbl_summary.set_markup(
            f"<span size='small' color='#94a3b8'>"
            f"Mostrando <b>{start_idx + 1 if total_items > 0 else 0} - {end_idx}</b> de <b>{total_items}</b> add-ons • <b>{num_installed}</b> instalados en el proyecto <b>{pname}</b>"
            f"</span>"
        )
        
        # Actualizar controles de paginación
        self.lbl_page_info.set_markup(
            f"<span size='small' color='#94a3b8'>"
            f"Página <b>{self.current_page}</b> de <b>{self.total_pages}</b> (Total: {total_items})"
            f"</span>"
        )
        self.lbl_current_page_badge.set_markup(f"<b>{self.current_page} / {self.total_pages}</b>")
        self.btn_first.set_sensitive(self.current_page > 1)
        self.btn_prev.set_sensitive(self.current_page > 1)
        self.btn_next.set_sensitive(self.current_page < self.total_pages)
        self.btn_last.set_sensitive(self.current_page < self.total_pages)
        
        if not filtered:
            self.content_stack.set_visible_child_name("empty")
            self.pagination_bar.hide()
            return
            
        self.pagination_bar.show_all()
        self.content_stack.set_visible_child_name("catalog")
        
        for addon in page_items:
            card = self.create_addon_card(addon)
            self.flowbox.add(card)
            
        self.flowbox.show_all()

    def create_addon_card(self, addon):
        installed = is_addon_installed(addon["title"], self.installed_addons)
        
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_box.get_style_context().add_class("addon-card")
        if installed:
            card_box.get_style_context().add_class("installed")
            
        card_box.set_size_request(280, 185)
        
        # 1. Cabecera de la tarjeta: Título y Badges
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Icono / Nombre
        icon_name = "emblem-default-symbolic" if addon["type"] == "official" else "emblem-package-symbolic"
        img_icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        header_row.pack_start(img_icon, False, False, 0)
        
        title_label = Gtk.Label()
        short_title = addon["title"].replace("ddev/", "")
        title_label.set_markup(f"<b>{short_title}</b>")
        title_label.set_tooltip_text(addon["title"])
        title_label.set_halign(Gtk.Align.START)
        title_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        header_row.pack_start(title_label, True, True, 0)
        
        # Badge Tipo: Oficial / Contrib
        lbl_type = Gtk.Label()
        if addon["type"] == "official":
            lbl_type.set_markup("<span size='xx-small' weight='bold'>OFICIAL</span>")
            lbl_type.get_style_context().add_class("badge")
            lbl_type.get_style_context().add_class("badge-addon-official")
        else:
            lbl_type.set_markup("<span size='xx-small' weight='bold'>CONTRIB</span>")
            lbl_type.get_style_context().add_class("badge")
            lbl_type.get_style_context().add_class("badge-addon-contrib")
        header_row.pack_start(lbl_type, False, False, 0)
        
        # Badge Estrellas
        stars = addon.get("stars", 0)
        if stars > 0:
            lbl_stars = Gtk.Label()
            lbl_stars.set_markup(f"<span size='xx-small'>⭐ {stars}</span>")
            lbl_stars.get_style_context().add_class("badge")
            lbl_stars.get_style_context().add_class("badge-addon-stars")
            header_row.pack_start(lbl_stars, False, False, 0)
            
        card_box.pack_start(header_row, False, False, 0)
        
        # 2. Sección "¿QUÉ HACE?": Descripción clara y detallada
        desc_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        desc_container.set_valign(Gtk.Align.START)
        
        lbl_what = Gtk.Label()
        lbl_what.set_markup("<span size='xx-small' weight='bold' color='#0284c7'>💡 ¿QUÉ HACE?</span>")
        lbl_what.set_halign(Gtk.Align.START)
        desc_container.pack_start(lbl_what, False, False, 0)
        
        lbl_desc = Gtk.Label()
        desc_text = addon.get("description") or "Extensión y servicio complementario para extender las capacidades de DDEV."
        lbl_desc.set_text(desc_text)
        lbl_desc.set_tooltip_text(f"{addon['title']}\n\n{desc_text}")
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_lines(3)
        lbl_desc.set_max_width_chars(36)
        lbl_desc.set_halign(Gtk.Align.START)
        lbl_desc.set_valign(Gtk.Align.START)
        lbl_desc.get_style_context().add_class("header-subtitle")
        desc_container.pack_start(lbl_desc, True, True, 0)
        
        card_box.pack_start(desc_container, True, True, 0)
        
        # 3. Estado de instalación
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_st = Gtk.Label()
        if installed:
            lbl_st.set_markup("<span size='x-small'>● Instalado en este proyecto</span>")
            lbl_st.get_style_context().add_class("badge")
            lbl_st.get_style_context().add_class("badge-addon-installed")
        else:
            lbl_st.set_markup("<span size='x-small'>○ Disponible</span>")
            lbl_st.get_style_context().add_class("badge")
            lbl_st.get_style_context().add_class("badge-addon-available")
        status_row.pack_start(lbl_st, False, False, 0)
        
        tag = addon.get("tag_name", "")
        if tag and tag != "latest":
            lbl_tag = Gtk.Label()
            lbl_tag.set_markup(f"<span size='xx-small' color='#94a3b8'>{tag}</span>")
            status_row.pack_end(lbl_tag, False, False, 0)
            
        card_box.pack_start(status_row, False, False, 0)
        
        # 4. Fila de Acciones
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if installed:
            btn_action = Gtk.Button()
            btn_action.get_style_context().add_class("badge-danger")
            b_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            b_box.pack_start(Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_box.pack_start(Gtk.Label(label="Desinstalar"), False, False, 0)
            btn_action.add(b_box)
            btn_action.connect("clicked", lambda b, ad=addon: self.on_remove_addon(ad))
            actions_row.pack_start(btn_action, True, True, 0)
        else:
            btn_action = Gtk.Button()
            btn_action.get_style_context().add_class("btn-primary")
            b_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            b_box.pack_start(Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_box.pack_start(Gtk.Label(label="Instalar con 1 Clic"), False, False, 0)
            btn_action.add(b_box)
            btn_action.connect("clicked", lambda b, ad=addon: self.on_install_addon(ad))
            actions_row.pack_start(btn_action, True, True, 0)
            
        github_url = addon.get("github_url", "")
        if github_url:
            btn_gh = Gtk.Button()
            btn_gh.add(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.BUTTON))
            btn_gh.set_tooltip_text(f"Ver documentación en GitHub ({github_url})")
            btn_gh.connect("clicked", lambda b, url=github_url: webbrowser.open(url))
            actions_row.pack_start(btn_gh, False, False, 0)
            
        card_box.pack_start(actions_row, False, False, 0)
        
        return card_box

    # -------------------------------------------------------------------------
    # Ejecución de Instalación y Desinstalación
    # -------------------------------------------------------------------------
    def on_install_addon(self, addon):
        if not self.current_project:
            self.show_error_dialog("Debes seleccionar un proyecto destino para instalar el add-on.")
            return
            
        approot = self.current_project.get("approot", "")
        pname = self.current_project.get("name", "")
        addon_title = addon["title"]
        
        dialog = ProgressDialog(self.main_app, title=f"Instalando {addon_title}")
        dialog.set_status(f"Descargando e instalando {addon_title} en {pname}...")
        
        def run_install():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t + "\n")
                    
                log(f"📁 Proyecto: {pname} ({approot})")
                log(f"📦 Add-on: {addon_title}")
                log("=" * 50)
                
                cmd_get = build_install_addon_command(addon_title)
                run_subproc(cmd_get, approot, dialog)
                
                log("\n" + "=" * 50)
                log("🔄 Reiniciando contenedores DDEV para aplicar los cambios...")
                cmd_restart = ["ddev", "restart", "-y"]
                run_subproc(cmd_restart, approot, dialog)
                
                log("\n" + "=" * 50)
                log(f"✅ ¡Add-on '{addon_title}' instalado y configurado con éxito!")
                GLib.idle_add(dialog.finish, True, f"Add-on {addon_title} instalado con éxito.", "", approot)
                GLib.idle_add(self.refresh_installed_for_current_project)
                GLib.idle_add(self.main_app.refresh_projects)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error al instalar add-on: {str(ex)}", "", approot)
                
        threading.Thread(target=run_install, daemon=True).start()

    def on_remove_addon(self, addon):
        if not self.current_project:
            return
            
        approot = self.current_project.get("approot", "")
        pname = self.current_project.get("name", "")
        addon_title = addon["title"]
        
        confirm = Gtk.MessageDialog(
            transient_for=self.main_app,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"¿Desinstalar '{addon_title}'?"
        )
        confirm.format_secondary_text(
            f"Se eliminarán los archivos de configuración asociados al add-on en {pname} y se reiniciará el proyecto."
        )
        res = confirm.run()
        confirm.destroy()
        
        if res != Gtk.ResponseType.YES:
            return
            
        dialog = ProgressDialog(self.main_app, title=f"Desinstalando {addon_title}")
        dialog.set_status(f"Eliminando {addon_title} de {pname}...")
        
        def run_remove():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t + "\n")
                    
                log(f"📁 Proyecto: {pname} ({approot})")
                log(f"🗑️ Eliminando Add-on: {addon_title}")
                log("=" * 50)
                
                cmd_rm = build_remove_addon_command(addon_title)
                run_subproc(cmd_rm, approot, dialog)
                
                log("\n" + "=" * 50)
                log("🔄 Reiniciando contenedores DDEV...")
                cmd_restart = ["ddev", "restart", "-y"]
                run_subproc(cmd_restart, approot, dialog)
                
                log("\n" + "=" * 50)
                log(f"✅ ¡Add-on '{addon_title}' desinstalado correctamente!")
                GLib.idle_add(dialog.finish, True, f"Add-on {addon_title} desinstalado.", "", approot)
                GLib.idle_add(self.refresh_installed_for_current_project)
                GLib.idle_add(self.main_app.refresh_projects)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error al desinstalar add-on: {str(ex)}", "", approot)
                
        threading.Thread(target=run_remove, daemon=True).start()

    def show_error_dialog(self, message):
        dlg = Gtk.MessageDialog(
            transient_for=self.main_app,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dlg.run()
        dlg.destroy()
