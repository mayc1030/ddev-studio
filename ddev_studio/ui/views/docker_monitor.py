# -*- coding: utf-8 -*-
"""
Vista del Monitor de Rendimiento y Recursos Docker en Vivo (Global y por Proyecto).
Muestra métricas en tiempo real de CPU, memoria, red y disco con actualización periódica no bloqueante.
"""

import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ddev_studio.core.docker_monitor import (
    get_live_docker_stats,
    format_bytes
)


class DockerMonitorView(Gtk.Box):
    def __init__(self, main_app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_app = main_app
        
        self.is_polling_active = True
        self.poll_interval = 2
        self.timer_id = None
        self.is_fetching = False
        
        self.selected_scope = "all"  # 'all', 'system', o nombre de proyecto
        self.cached_stats = None
        self.known_projects = []
        
        self.build_ui()
        
        # Iniciar primer fetch y polling
        GLib.idle_add(self.refresh_stats)
        self.start_polling()

    def build_ui(self):
        # 1. Barra de Cabecera y Controles
        header_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        header_card.get_style_context().add_class("marketplace-header-box")
        
        # Fila superior: Título y controles en vivo
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span size='large' weight='bold'>📊 Monitor de Recursos Docker en Vivo</span>")
        lbl_title.set_halign(Gtk.Align.START)
        title_box.pack_start(lbl_title, False, False, 0)
        
        lbl_sub = Gtk.Label()
        lbl_sub.set_markup("<span color='#94a3b8' size='small'>Supervisión de CPU, RAM, Red y Disco por proyecto y global.</span>")
        lbl_sub.set_halign(Gtk.Align.START)
        title_box.pack_start(lbl_sub, False, False, 0)
        top_row.pack_start(title_box, True, True, 0)
        
        # Toggle en vivo (Switch)
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_sw = Gtk.Label(label="En vivo:")
        lbl_sw.get_style_context().add_class("header-subtitle")
        switch_box.pack_start(lbl_sw, False, False, 0)
        
        self.switch_live = Gtk.Switch()
        self.switch_live.set_active(True)
        self.switch_live.set_tooltip_text("Activar o pausar actualización automática cada 2 segundos")
        self.switch_live.connect("state-set", self.on_switch_toggled)
        switch_box.pack_start(self.switch_live, False, False, 0)
        top_row.pack_start(switch_box, False, False, 0)
        
        # Botón actualizar manual
        self.btn_refresh = Gtk.Button()
        self.btn_refresh.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        self.btn_refresh.set_tooltip_text("Actualizar métricas ahora")
        self.btn_refresh.connect("clicked", lambda b: self.refresh_stats())
        top_row.pack_start(self.btn_refresh, False, False, 0)
        
        header_card.pack_start(top_row, False, False, 0)
        
        # Fila de Filtro de Ámbito / Proyecto
        filter_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_scope = Gtk.Label(label="Ámbito / Proyecto:")
        lbl_scope.set_halign(Gtk.Align.START)
        filter_row.pack_start(lbl_scope, False, False, 0)
        
        self.combo_scope = Gtk.ComboBoxText()
        self.combo_scope.set_size_request(260, -1)
        self.combo_scope.append("all", "🌐 Vista Global (Todos los contenedores)")
        self.combo_scope.append("system", "⚙️ DDEV Sistema (Router, SSH-Agent)")
        self.combo_scope.set_active_id("all")
        self.combo_scope.connect("changed", self.on_scope_changed)
        filter_row.pack_start(self.combo_scope, False, False, 0)
        
        self.lbl_docker_status = Gtk.Label()
        self.lbl_docker_status.set_markup("<span size='small' color='#10b981'>● Docker Engine activo</span>")
        filter_row.pack_end(self.lbl_docker_status, False, False, 0)
        
        header_card.pack_start(filter_row, False, False, 0)
        self.pack_start(header_card, False, False, 0)
        
        # 2. Fila de 4 Tarjetas KPI (Métricas en vivo)
        kpi_grid = Gtk.Grid()
        kpi_grid.set_column_spacing(12)
        kpi_grid.set_row_spacing(8)
        kpi_grid.set_column_homogeneous(True)
        
        # KPI 1: CPU Total
        self.card_cpu = self.create_kpi_card("⚡ CPU TOTAL", "0.0%", "0% del sistema")
        self.pbar_cpu = Gtk.ProgressBar()
        self.pbar_cpu.set_fraction(0.0)
        self.card_cpu.pack_end(self.pbar_cpu, False, False, 0)
        kpi_grid.attach(self.card_cpu, 0, 0, 1, 1)
        
        # KPI 2: Memoria RAM
        self.card_mem = self.create_kpi_card("🧠 MEMORIA RAM", "0 B", "0% asignado")
        self.pbar_mem = Gtk.ProgressBar()
        self.pbar_mem.set_fraction(0.0)
        self.card_mem.pack_end(self.pbar_mem, False, False, 0)
        kpi_grid.attach(self.card_mem, 1, 0, 1, 1)
        
        # KPI 3: Contenedores
        self.card_containers = self.create_kpi_card("📦 CONTENEDORES", "0 activos", "DDEV y sistema")
        kpi_grid.attach(self.card_containers, 2, 0, 1, 1)
        
        # KPI 4: Red e I/O
        self.card_io = self.create_kpi_card("🌐 / 💾 RED Y DISCO", "Net: 0 B / 0 B", "Disco: 0 B / 0 B")
        kpi_grid.attach(self.card_io, 3, 0, 1, 1)
        
        self.pack_start(kpi_grid, False, False, 0)
        
        # 3. Tabla Interactiva de Contenedores
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(200)
        scrolled.get_style_context().add_class("monitor-treeview")
        
        # Columnas del ListStore:
        # 0: icon_name, 1: project, 2: service, 3: cpu_pct (float), 4: cpu_str,
        # 5: mem_bytes (float), 6: mem_str, 7: net_io, 8: block_io, 9: pids (int), 10: container_id
        self.store = Gtk.ListStore(str, str, str, float, str, float, str, str, str, int, str)
        
        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)
        
        # Columna Ámbito / Proyecto
        col_proj = Gtk.TreeViewColumn("Ámbito / Proyecto")
        col_proj.set_sort_column_id(1)
        cell_icon = Gtk.CellRendererPixbuf()
        col_proj.pack_start(cell_icon, False)
        col_proj.add_attribute(cell_icon, "icon_name", 0)
        cell_proj = Gtk.CellRendererText()
        cell_proj.set_property("weight", 600)
        col_proj.pack_start(cell_proj, True)
        col_proj.add_attribute(cell_proj, "text", 1)
        self.treeview.append_column(col_proj)
        
        # Columna Servicio / Nombre
        col_serv = Gtk.TreeViewColumn("Servicio / Contenedor")
        col_serv.set_sort_column_id(2)
        cell_serv = Gtk.CellRendererText()
        col_serv.pack_start(cell_serv, True)
        col_serv.add_attribute(cell_serv, "text", 2)
        self.treeview.append_column(col_serv)
        
        # Columna CPU %
        col_cpu = Gtk.TreeViewColumn("CPU %")
        col_cpu.set_sort_column_id(3)
        cell_cpu = Gtk.CellRendererText()
        cell_cpu.set_property("weight", 700)
        col_cpu.pack_start(cell_cpu, True)
        col_cpu.add_attribute(cell_cpu, "text", 4)
        self.treeview.append_column(col_cpu)
        
        # Columna Memoria RAM
        col_mem = Gtk.TreeViewColumn("Memoria RAM")
        col_mem.set_sort_column_id(5)
        cell_mem = Gtk.CellRendererText()
        col_mem.pack_start(cell_mem, True)
        col_mem.add_attribute(cell_mem, "text", 6)
        self.treeview.append_column(col_mem)
        
        # Columna Red I/O
        col_net = Gtk.TreeViewColumn("Red I/O (In / Out)")
        col_net.set_sort_column_id(7)
        cell_net = Gtk.CellRendererText()
        col_net.pack_start(cell_net, True)
        col_net.add_attribute(cell_net, "text", 7)
        self.treeview.append_column(col_net)
        
        # Columna Disco I/O
        col_disk = Gtk.TreeViewColumn("Disco I/O")
        col_disk.set_sort_column_id(8)
        cell_disk = Gtk.CellRendererText()
        col_disk.pack_start(cell_disk, True)
        col_disk.add_attribute(cell_disk, "text", 8)
        self.treeview.append_column(col_disk)
        
        # Columna PIDs
        col_pids = Gtk.TreeViewColumn("Hilos (PIDs)")
        col_pids.set_sort_column_id(9)
        cell_pids = Gtk.CellRendererText()
        col_pids.pack_start(cell_pids, True)
        col_pids.add_attribute(cell_pids, "text", 9)
        self.treeview.append_column(col_pids)
        
        scrolled.add(self.treeview)
        self.pack_start(scrolled, True, True, 0)

    def create_kpi_card(self, title, initial_val, initial_sub):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        card.get_style_context().add_class("kpi-card")
        
        lbl_t = Gtk.Label()
        lbl_t.set_markup(f"<span size='small' weight='bold' color='#94a3b8'>{title}</span>")
        lbl_t.set_halign(Gtk.Align.START)
        card.pack_start(lbl_t, False, False, 0)
        
        lbl_v = Gtk.Label()
        lbl_v.set_markup(f"<span size='x-large' weight='bold'>{initial_val}</span>")
        lbl_v.set_halign(Gtk.Align.START)
        card.lbl_val = lbl_v
        card.pack_start(lbl_v, False, False, 0)
        
        lbl_s = Gtk.Label()
        lbl_s.set_markup(f"<span size='small' color='#94a3b8'>{initial_sub}</span>")
        lbl_s.set_halign(Gtk.Align.START)
        card.lbl_sub = lbl_s
        card.pack_start(lbl_s, False, False, 0)
        
        return card

    # -------------------------------------------------------------------------
    # Gestión de Proyectos y Ámbitos
    # -------------------------------------------------------------------------
    def update_projects(self, projects):
        """
        Sincroniza la lista de proyectos con el selector de ámbito.
        """
        self.known_projects = [p.get("name", "") for p in (projects or []) if p.get("name")]
        current_id = self.combo_scope.get_active_id() or "all"
        
        self.combo_scope.remove_all()
        self.combo_scope.append("all", "🌐 Vista Global (Todos los contenedores)")
        self.combo_scope.append("system", "⚙️ DDEV Sistema (Router, SSH-Agent)")
        
        for pname in self.known_projects:
            self.combo_scope.append(pname, f"📁 Proyecto: {pname}")
            
        # Preservar selección previa si existe
        if current_id in ["all", "system"] or current_id in self.known_projects:
            self.combo_scope.set_active_id(current_id)
        else:
            self.combo_scope.set_active_id("all")

    def on_scope_changed(self, combo):
        active_id = combo.get_active_id()
        if active_id:
            self.selected_scope = active_id
            self.apply_stats_to_ui()

    # -------------------------------------------------------------------------
    # Temporizador de Monitoreo en Vivo (Polling)
    # -------------------------------------------------------------------------
    def start_polling(self):
        if not self.timer_id:
            self.timer_id = GLib.timeout_add_seconds(self.poll_interval, self.on_poll_timer)

    def stop_polling(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None

    def resume_polling(self):
        if self.switch_live.get_active() and not self.timer_id:
            self.start_polling()
            self.refresh_stats()

    def pause_polling(self):
        self.stop_polling()

    def on_switch_toggled(self, switch, state):
        self.is_polling_active = state
        if state:
            self.start_polling()
            self.refresh_stats()
        else:
            self.stop_polling()

    def on_poll_timer(self):
        if not self.is_polling_active:
            return False  # Cancela el temporizador
            
        self.refresh_stats()
        return True  # Mantiene el temporizador activo

    # -------------------------------------------------------------------------
    # Consulta de Estadísticas
    # -------------------------------------------------------------------------
    def refresh_stats(self):
        if self.is_fetching:
            return
            
        self.is_fetching = True
        
        def task():
            stats = get_live_docker_stats()
            def done():
                self.is_fetching = False
                self.cached_stats = stats
                self.apply_stats_to_ui()
            GLib.idle_add(done)
            
        threading.Thread(target=task, daemon=True).start()

    def apply_stats_to_ui(self):
        if not self.cached_stats:
            return
            
        stats = self.cached_stats
        
        # Comprobar disponibilidad de Docker
        if not stats.get("is_docker_available", False):
            err_msg = stats.get("error_message", "Docker no disponible.")
            self.lbl_docker_status.set_markup(f"<span size='small' color='#ef4444'>● {err_msg}</span>")
            self.card_cpu.lbl_val.set_markup("<span size='x-large' weight='bold'>--</span>")
            self.card_mem.lbl_val.set_markup("<span size='x-large' weight='bold'>--</span>")
            self.card_containers.lbl_val.set_markup("<span size='x-large' weight='bold'>0</span>")
            self.store.clear()
            return
            
        self.lbl_docker_status.set_markup("<span size='small' color='#10b981'>● Docker Engine activo</span>")
        
        containers = stats.get("containers", [])
        projects_map = stats.get("projects", {})
        global_sum = stats.get("global_summary", {})
        
        # Filtrar según ámbito seleccionado
        filtered_containers = []
        if self.selected_scope == "all":
            filtered_containers = containers
            cpu_val = global_sum["total_cpu_pct"]
            mem_val_str = f"{global_sum['total_mem_str']} / {global_sum['total_limit_str']}"
            mem_pct = global_sum["mem_percent"]
            count_str = f"{global_sum['container_count']} activos"
            count_sub = f"{global_sum['ddev_container_count']} de DDEV"
            net_str = f"Net: {global_sum['total_net_str']}"
            block_str = f"Disco: {global_sum['total_block_str']}"
        elif self.selected_scope == "system":
            filtered_containers = [c for c in containers if c["scope"] == "system"]
            proj_data = projects_map.get("DDEV Sistema", {})
            cpu_val = proj_data.get("total_cpu_pct", 0.0)
            mem_val_str = f"{proj_data.get('total_mem_str', '0 B')} / {global_sum['total_limit_str']}"
            mem_pct = proj_data.get("mem_percent", 0.0)
            count_str = f"{len(filtered_containers)} activos"
            count_sub = "Traefik Router y SSH Agent"
            net_str = "Infraestructura DDEV"
            block_str = "Core de red"
        else:
            # Proyecto específico
            filtered_containers = [c for c in containers if c["project"] == self.selected_scope]
            proj_data = projects_map.get(self.selected_scope, {})
            cpu_val = proj_data.get("total_cpu_pct", 0.0)
            mem_val_str = f"{proj_data.get('total_mem_str', '0 B')} / {global_sum['total_limit_str']}"
            mem_pct = proj_data.get("mem_percent", 0.0)
            count_str = f"{len(filtered_containers)} activos"
            count_sub = f"Proyecto '{self.selected_scope}'"
            net_str = f"Contenedores: {len(filtered_containers)}"
            block_str = "DDEV Project"
            
        # 1. Actualizar Tarjetas KPI
        # CPU
        cpu_color = "#10b981" if cpu_val < 60 else ("#f59e0b" if cpu_val < 85 else "#ef4444")
        self.card_cpu.lbl_val.set_markup(f"<span size='x-large' weight='bold' color='{cpu_color}'>{cpu_val:.2f}%</span>")
        self.pbar_cpu.set_fraction(min(1.0, cpu_val / 100.0))
        self.card_cpu.lbl_sub.set_markup(f"<span size='small' color='#94a3b8'>{self.selected_scope if self.selected_scope != 'all' else 'Global'}</span>")
        
        # RAM
        mem_color = "#10b981" if mem_pct < 60 else ("#f59e0b" if mem_pct < 85 else "#ef4444")
        self.card_mem.lbl_val.set_markup(f"<span size='x-large' weight='bold' color='{mem_color}'>{mem_val_str}</span>")
        self.pbar_mem.set_fraction(min(1.0, mem_pct / 100.0))
        self.card_mem.lbl_sub.set_markup(f"<span size='small' color='#94a3b8'>{mem_pct:.1f}% del límite asignado</span>")
        
        # Contenedores
        self.card_containers.lbl_val.set_markup(f"<span size='x-large' weight='bold'>{count_str}</span>")
        self.card_containers.lbl_sub.set_markup(f"<span size='small' color='#94a3b8'>{count_sub}</span>")
        
        # I/O
        self.card_io.lbl_val.set_markup(f"<span size='medium' weight='bold'>{net_str}</span>")
        self.card_io.lbl_sub.set_markup(f"<span size='small' color='#94a3b8'>{block_str}</span>")
        
        # 2. Actualizar Tabla de Contenedores
        self.store.clear()
        for c in filtered_containers:
            icon_name = "network-server-symbolic" if c["scope"] == "system" else ("folder-symbolic" if c["scope"] == "project" else "emblem-package-symbolic")
            cpu_fmt = f"{c['cpu_percent']:.2f}%"
            mem_fmt = f"{c['mem_used_str']} ({c['mem_percent']:.1f}%)"
            
            self.store.append([
                icon_name,
                c["project"],
                f"{c['service']} ({c['name']})",
                c["cpu_percent"],
                cpu_fmt,
                c["mem_used_bytes"],
                mem_fmt,
                c["net_io"],
                c["block_io"],
                c["pids"],
                c["id"]
            ])
