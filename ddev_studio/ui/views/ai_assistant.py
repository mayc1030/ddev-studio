# -*- coding: utf-8 -*-
"""
Vista del Asistente de IA Local y Centro de Consultas para DDEV Studio.
Módulo completamente desacoplado basado en Ollama (privado, offline y local).
"""

import subprocess
import threading
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

from ddev_studio.core.ai_client import (
    OllamaClient,
    CATALOG_RECOMMENDED_MODELS,
    DEFAULT_OLLAMA_HOST,
)
from ddev_studio.core.terminal import open_terminal
from ddev_studio.ui.dialogs.progress import ProgressDialog


class AIAssistantView(Gtk.Box):
    def __init__(self, main_app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.main_app = main_app
        self.client = OllamaClient()

        self.messages = []
        self.is_generating = False
        self.cancel_event = None
        self.installed_models = []
        self.active_model = ""
        self.active_project_data = {}
        self.current_assistant_label = None
        self.current_assistant_text = ""

        # Contenedor principal con márgenes
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(10)
        self.set_margin_bottom(12)

        # 1. Barra Superior de Control
        self.top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.top_bar.get_style_context().add_class("nav-bar-box")
        self.pack_start(self.top_bar, False, False, 0)

        # Icono y Título
        lbl_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        img_brain = Gtk.Image.new_from_icon_name("help-browser-symbolic", Gtk.IconSize.BUTTON)
        lbl_title_box.pack_start(img_brain, False, False, 0)
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<b>Asistente IA Local</b>")
        lbl_title_box.pack_start(lbl_title, False, False, 0)
        self.top_bar.pack_start(lbl_title_box, False, False, 0)

        # Badge de Estado
        self.lbl_status = Gtk.Label(label="Comprobando...")
        self.lbl_status.get_style_context().add_class("badge")
        self.top_bar.pack_start(self.lbl_status, False, False, 0)

        # Selector de Modelo
        lbl_m = Gtk.Label(label="Modelo:")
        self.top_bar.pack_start(lbl_m, False, False, 0)

        self.combo_models = Gtk.ComboBoxText()
        self.combo_models.set_tooltip_text("Selecciona el modelo LLM instalado en tu Ollama local")
        self.combo_models.connect("changed", self._on_model_changed)
        self.top_bar.pack_start(self.combo_models, False, False, 0)

        # Botón Descargar otro modelo
        self.btn_more_models = Gtk.Button()
        b_mm = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_mm.pack_start(Gtk.Image.new_from_icon_name("software-update-available-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_mm.pack_start(Gtk.Label(label="Modelos..."), False, False, 0)
        self.btn_more_models.add(b_mm)
        self.btn_more_models.get_style_context().add_class("btn-quick")
        self.btn_more_models.set_tooltip_text("Ver catálogo y descargar nuevos modelos locales")
        self.btn_more_models.connect("clicked", lambda b: self._show_models_catalog_dialog())
        self.top_bar.pack_start(self.btn_more_models, False, False, 0)

        # Espaciador central
        spacer = Gtk.Box()
        self.top_bar.pack_start(spacer, True, True, 0)

        # Checkbox contexto de proyecto
        self.chk_context = Gtk.CheckButton(label="Incluir contexto de:")
        self.chk_context.set_tooltip_text("Al activar, la IA sabrá la tecnología, versión de PHP/Node y estructura del proyecto elegido")
        self.chk_context.connect("toggled", self._on_context_toggled)
        self.top_bar.pack_start(self.chk_context, False, False, 0)

        self.combo_projects = Gtk.ComboBoxText()
        self.combo_projects.set_sensitive(False)
        self.combo_projects.connect("changed", self._on_project_changed)
        self.top_bar.pack_start(self.combo_projects, False, False, 0)

        # Botón Limpiar conversación
        btn_clear = Gtk.Button()
        b_cl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_cl.pack_start(Gtk.Image.new_from_icon_name("edit-clear-all-symbolic", Gtk.IconSize.MENU), False, False, 0)
        b_cl.pack_start(Gtk.Label(label="Nueva Consulta"), False, False, 0)
        btn_clear.add(b_cl)
        btn_clear.get_style_context().add_class("btn-quick")
        btn_clear.set_tooltip_text("Iniciar una nueva conversación desde cero")
        btn_clear.connect("clicked", lambda b: self.clear_chat())
        self.top_bar.pack_start(btn_clear, False, False, 0)

        # Botón refrescar estado de Ollama
        btn_refresh = Gtk.Button()
        btn_refresh.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.MENU))
        btn_refresh.set_tooltip_text("Comprobar conexión y modelos de Ollama")
        btn_refresh.connect("clicked", lambda b: self.refresh_state())
        self.top_bar.pack_start(btn_refresh, False, False, 0)

        # 2. Stack Principal de Estados (Onboarding vs No Models vs Chat)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.pack_start(self.stack, True, True, 6)

        # Estado A: Onboarding / Instalar Ollama
        self.view_onboarding = self._build_onboarding_ui()
        self.stack.add_named(self.view_onboarding, "onboarding")

        # Estado B: Sin modelos descargados
        self.view_no_models = self._build_no_models_ui()
        self.stack.add_named(self.view_no_models, "no_models")

        # Estado C: Chat / Consultas Activo
        self.view_chat = self._build_chat_ui()
        self.stack.add_named(self.view_chat, "chat")

        # Comprobación inicial de estado en segundo plano
        GLib.idle_add(self.refresh_state)

    # -------------------------------------------------------------------------
    # Construcción de Sub-Vistas (Estados de la Pila)
    # -------------------------------------------------------------------------
    def _build_onboarding_ui(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(24)
        box.set_margin_bottom(24)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.get_style_context().add_class("option-highlight-box")
        card.set_size_request(580, -1)

        row_h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        img_big = Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.DIALOG)
        row_h.pack_start(img_big, False, False, 0)

        v_t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_c_t = Gtk.Label()
        lbl_c_t.set_markup("<b><big>Centro de Consultas y Asistente IA Local</big></b>")
        lbl_c_t.set_halign(Gtk.Align.START)
        v_t.pack_start(lbl_c_t, False, False, 0)

        lbl_sub = Gtk.Label(label="Potenciado por Ollama • 100% Privado • Sin cuotas ni API Keys • Totalmente Offline")
        lbl_sub.set_halign(Gtk.Align.START)
        v_t.pack_start(lbl_sub, False, False, 0)
        row_h.pack_start(v_t, True, True, 0)
        card.pack_start(row_h, False, False, 0)

        lbl_desc = Gtk.Label()
        lbl_desc.set_markup(
            "Consulta sobre cualquier tema de desarrollo, arquitectura de software, comandos de Linux, bases de datos o solución de problemas directamente dentro de DDEV Studio.\n\n"
            "Para activar esta funcionalidad, necesitas tener en ejecución el motor local <b>Ollama</b> en tu sistema."
        )
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_halign(Gtk.Align.START)
        card.pack_start(lbl_desc, False, False, 0)

        # Botones de Acción según si está instalado el binario
        self.box_onboarding_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.box_onboarding_actions.set_margin_top(8)

        self.btn_install_ollama = Gtk.Button()
        b_in = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_in.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_in.pack_start(Gtk.Label(label="Instalar Ollama en tu Sistema"), False, False, 0)
        self.btn_install_ollama.add(b_in)
        self.btn_install_ollama.get_style_context().add_class("btn-primary")
        self.btn_install_ollama.connect("clicked", lambda b: self.install_ollama())
        self.box_onboarding_actions.pack_start(self.btn_install_ollama, False, False, 0)

        self.btn_install_term = Gtk.Button()
        b_it = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_it.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_it.pack_start(Gtk.Label(label="Instalar en Terminal"), False, False, 0)
        self.btn_install_term.add(b_it)
        self.btn_install_term.connect("clicked", lambda b: self.install_ollama_terminal())
        self.box_onboarding_actions.pack_start(self.btn_install_term, False, False, 0)

        self.btn_start_ollama = Gtk.Button()
        b_st = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_st.pack_start(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_st.pack_start(Gtk.Label(label="Iniciar Servicio Ollama"), False, False, 0)
        self.btn_start_ollama.add(b_st)
        self.btn_start_ollama.get_style_context().add_class("btn-start")
        self.btn_start_ollama.connect("clicked", lambda b: self.start_ollama_service())
        self.box_onboarding_actions.pack_start(self.btn_start_ollama, False, False, 0)

        btn_check = Gtk.Button(label="Comprobar Conexión")
        btn_check.connect("clicked", lambda b: self.refresh_state())
        self.box_onboarding_actions.pack_start(btn_check, False, False, 0)

        card.pack_start(self.box_onboarding_actions, False, False, 0)
        box.pack_start(card, False, False, 0)

        scrolled.add(box)
        return scrolled

    def _build_no_models_ui(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(16)
        box.set_margin_bottom(16)

        banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_b_t = Gtk.Label()
        lbl_b_t.set_markup("<b><big>Ollama está conectado. Elige tu primer modelo de IA</big></b>")
        lbl_b_t.set_halign(Gtk.Align.START)
        banner.pack_start(lbl_b_t, False, False, 0)

        lbl_b_s = Gtk.Label(label="Los modelos se descargan una única vez y se ejecutan 100% de forma local en tu máquina.")
        lbl_b_s.set_halign(Gtk.Align.START)
        banner.pack_start(lbl_b_s, False, False, 0)
        box.pack_start(banner, False, False, 0)

        # Cuadrícula de modelos recomendados
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(2)
        flow.set_min_children_per_line(1)
        flow.set_row_spacing(10)
        flow.set_column_spacing(12)
        flow.set_homogeneous(True)

        for m_data in CATALOG_RECOMMENDED_MODELS:
            m_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            m_card.get_style_context().add_class("module-item-box")

            r_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl_name = Gtk.Label()
            lbl_name.set_markup(f"<b>{m_data['label']}</b>")
            lbl_name.set_halign(Gtk.Align.START)
            r_top.pack_start(lbl_name, True, True, 0)

            badge_ram = Gtk.Label(label=m_data['ram_req'])
            badge_ram.get_style_context().add_class("badge")
            r_top.pack_start(badge_ram, False, False, 0)

            badge_size = Gtk.Label(label=m_data['size_str'])
            badge_size.get_style_context().add_class("badge")
            r_top.pack_start(badge_size, False, False, 0)
            m_card.pack_start(r_top, False, False, 0)

            lbl_desc = Gtk.Label(label=m_data['tagline'])
            lbl_desc.set_line_wrap(True)
            lbl_desc.set_halign(Gtk.Align.START)
            m_card.pack_start(lbl_desc, False, False, 0)

            btn_dl = Gtk.Button()
            btn_dl.get_style_context().add_class("btn-quick")
            btn_dl.get_style_context().add_class("btn-quick-cache")
            b_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_box.pack_start(Gtk.Image.new_from_icon_name("software-update-available-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
            b_box.pack_start(Gtk.Label(label=f"Descargar {m_data['label']}"), False, False, 0)
            btn_dl.add(b_box)
            btn_dl.connect("clicked", lambda b, mn=m_data['name']: self.download_model(mn))
            btn_dl.set_halign(Gtk.Align.START)
            btn_dl.set_margin_top(4)
            m_card.pack_start(btn_dl, False, False, 0)

            flow.add(m_card)

        box.pack_start(flow, False, False, 0)
        scrolled.add(box)
        return scrolled

    def _build_chat_ui(self) -> Gtk.Widget:
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # Scrolled Chat Messages
        self.chat_scrolled = Gtk.ScrolledWindow()
        self.chat_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.chat_scrolled.set_vexpand(True)

        self.chat_messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.chat_messages_box.set_margin_start(12)
        self.chat_messages_box.set_margin_end(12)
        self.chat_messages_box.set_margin_top(10)
        self.chat_messages_box.set_margin_bottom(10)

        # Tarjeta de bienvenida inicial en el chat
        self.welcome_widget = self._build_chat_welcome_widget()
        self.chat_messages_box.pack_start(self.welcome_widget, False, False, 0)

        self.chat_scrolled.add(self.chat_messages_box)
        container.pack_start(self.chat_scrolled, True, True, 0)

        # Barra de Entrada Inferior
        input_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        input_container.get_style_context().add_class("chat-input-box")

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_row.set_margin_start(6)
        input_row.set_margin_end(6)
        input_row.set_margin_top(6)
        input_row.set_margin_bottom(6)

        # TextView multilínea
        scrolled_text = Gtk.ScrolledWindow()
        scrolled_text.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_text.set_size_request(-1, 55)

        self.text_input = Gtk.TextView()
        self.text_input.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_input.connect("key-press-event", self._on_input_key_pressed)
        scrolled_text.add(self.text_input)
        input_row.pack_start(scrolled_text, True, True, 0)

        # Botones de envío y control
        btn_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        btn_vbox.set_valign(Gtk.Align.CENTER)

        self.btn_send = Gtk.Button()
        b_send = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_send.pack_start(Gtk.Image.new_from_icon_name("mail-send-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_send.pack_start(Gtk.Label(label="Preguntar"), False, False, 0)
        self.btn_send.add(b_send)
        self.btn_send.get_style_context().add_class("btn-primary")
        self.btn_send.set_tooltip_text("Enviar consulta a la IA (Atajo: Ctrl + Enter)")
        self.btn_send.connect("clicked", lambda b: self.send_message())
        btn_vbox.pack_start(self.btn_send, False, False, 0)

        self.btn_stop = Gtk.Button()
        b_stop = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        b_stop.pack_start(Gtk.Image.new_from_icon_name("process-stop-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_stop.pack_start(Gtk.Label(label="Detener"), False, False, 0)
        self.btn_stop.add(b_stop)
        self.btn_stop.get_style_context().add_class("btn-stop")
        self.btn_stop.set_no_show_all(True)
        self.btn_stop.set_visible(False)
        self.btn_stop.connect("clicked", lambda b: self.stop_generation())
        btn_vbox.pack_start(self.btn_stop, False, False, 0)

        self.spinner = Gtk.Spinner()
        self.spinner.set_no_show_all(True)
        self.spinner.set_visible(False)
        btn_vbox.pack_start(self.spinner, False, False, 0)

        input_row.pack_start(btn_vbox, False, False, 0)
        input_container.pack_start(input_row, False, False, 0)

        container.pack_start(input_container, False, False, 0)
        return container

    def _build_chat_welcome_widget(self) -> Gtk.Widget:
        w_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        w_box.set_margin_top(16)
        w_box.set_margin_bottom(16)
        w_box.get_style_context().add_class("project-card")

        lbl_hi = Gtk.Label()
        lbl_hi.set_markup("<b><big>¿Qué tema deseas consultar o investigar hoy?</big></b>")
        lbl_hi.set_halign(Gtk.Align.START)
        w_box.pack_start(lbl_hi, False, False, 0)

        lbl_sug = Gtk.Label(label="Puedes preguntar sobre cualquier concepto, diseño de arquitectura, Linux, Docker o comandos. Aquí tienes algunas ideas rápidas:")
        lbl_sug.set_halign(Gtk.Align.START)
        lbl_sug.set_line_wrap(True)
        w_box.pack_start(lbl_sug, False, False, 0)

        suggestions = [
            "Explícame cómo funciona WebSockets y el reverse proxy en Nginx con ejemplos",
            "¿Cuáles son las diferencias y cuándo elegir SQLite, MariaDB o PostgreSQL?",
            "Explícame qué es Domain-Driven Design (DDD) y Arquitectura Hexagonal",
            "¿Cómo optimizar el uso de RAM y rendimiento de Docker en Linux?"
        ]

        flow_sug = Gtk.FlowBox()
        flow_sug.set_selection_mode(Gtk.SelectionMode.NONE)
        flow_sug.set_max_children_per_line(2)
        flow_sug.set_row_spacing(6)
        flow_sug.set_column_spacing(8)
        flow_sug.set_homogeneous(True)

        for s in suggestions:
            btn_s = Gtk.Button()
            btn_s.get_style_context().add_class("btn-quick")
            lbl_btn = Gtk.Label(label=s)
            lbl_btn.set_line_wrap(True)
            lbl_btn.set_xalign(0.0)
            btn_s.add(lbl_btn)
            btn_s.connect("clicked", lambda b, text=s: self._use_suggestion(text))
            flow_sug.add(btn_s)

        w_box.pack_start(flow_sug, False, False, 0)
        return w_box

    # -------------------------------------------------------------------------
    # Gestión de Estados y Modelos
    # -------------------------------------------------------------------------
    def refresh_state(self):
        """Comprueba el estado de Ollama en segundo plano y conmuta la vista adecuada."""
        def task():
            is_bin = self.client.is_binary_installed()
            is_running = self.client.is_server_running()
            models = self.client.list_installed_models() if is_running else []

            def update_ui():
                self.installed_models = models
                # Actualizar acciones en onboarding
                if hasattr(self, "btn_install_ollama"):
                    self.btn_install_ollama.set_visible(not is_bin)
                if hasattr(self, "btn_install_term"):
                    self.btn_install_term.set_visible(not is_bin)
                if hasattr(self, "btn_start_ollama"):
                    self.btn_start_ollama.set_visible(is_bin and not is_running)

                # Actualizar badge y combo
                ctx = self.lbl_status.get_style_context()
                ctx.remove_class("badge-running")
                ctx.remove_class("badge-stopped")

                if not is_running:
                    self.lbl_status.set_text("OLLAMA DESCONECTADO")
                    ctx.add_class("badge-stopped")
                    self.stack.set_visible_child_name("onboarding")
                elif not models:
                    self.lbl_status.set_text("OLLAMA CONECTADO (SIN MODELOS)")
                    ctx.add_class("badge-running")
                    self.stack.set_visible_child_name("no_models")
                else:
                    self.lbl_status.set_text("IA LOCAL CONECTADA")
                    ctx.add_class("badge-running")
                    self.stack.set_visible_child_name("chat")

                    # Actualizar combo de modelos
                    cur_sel = self.combo_models.get_active_text()
                    self.combo_models.remove_all()
                    for m in models:
                        self.combo_models.append_text(m["name"])

                    if models:
                        if cur_sel and cur_sel in [m["name"] for m in models]:
                            self.combo_models.set_active_id(cur_sel)
                        else:
                            self.combo_models.set_active(0)
                        self.active_model = self.combo_models.get_active_text() or ""

                self.populate_projects()

            GLib.idle_add(update_ui)

        threading.Thread(target=task, daemon=True).start()

    def populate_projects(self):
        """Llena la lista de proyectos conocidos para la opción de contexto."""
        if not hasattr(self.main_app, "projects_cache"):
            return
        projects = getattr(self.main_app, "projects_cache", [])
        cur = self.combo_projects.get_active_text()
        self.combo_projects.remove_all()
        for p in projects:
            pname = p.get("name", "")
            if pname:
                self.combo_projects.append_text(pname)
        if projects:
            if cur:
                self.combo_projects.set_active_id(cur)
            else:
                self.combo_projects.set_active(0)

    def _on_model_changed(self, combo):
        self.active_model = combo.get_active_text() or ""

    def _on_context_toggled(self, chk):
        active = chk.get_active()
        self.combo_projects.set_sensitive(active)
        self._on_project_changed(self.combo_projects)

    def _on_project_changed(self, combo):
        pname = combo.get_active_text()
        projects = getattr(self.main_app, "projects_cache", [])
        self.active_project_data = next((p for p in projects if p.get("name") == pname), {})

    def _use_suggestion(self, text):
        buf = self.text_input.get_buffer()
        buf.set_text(text)
        self.send_message()

    def _show_models_catalog_dialog(self):
        dialog = Gtk.Dialog(
            title="Gestión de Modelos de IA Local (Ollama)",
            transient_for=self.main_app,
            modal=True,
        )
        dialog.set_default_size(560, 420)
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup("<b><big>Catálogo de Modelos Recomendados</big></b>")
        lbl.set_halign(Gtk.Align.START)
        box.pack_start(lbl, False, False, 0)

        for m_data in CATALOG_RECOMMENDED_MODELS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.get_style_context().add_class("module-item-box")

            v_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lbl_n = Gtk.Label()
            lbl_n.set_markup(f"<b>{m_data['label']}</b> ({m_data['size_str']}) - <small>{m_data['ram_req']}</small>")
            lbl_n.set_halign(Gtk.Align.START)
            v_info.pack_start(lbl_n, False, False, 0)

            lbl_d = Gtk.Label(label=m_data['tagline'])
            lbl_d.set_line_wrap(True)
            lbl_d.set_halign(Gtk.Align.START)
            v_info.pack_start(lbl_d, False, False, 0)
            row.pack_start(v_info, True, True, 0)

            is_already = any(m["name"].startswith(m_data["name"].split(":")[0]) for m in self.installed_models)
            if is_already:
                lbl_in = Gtk.Label(label="Instalado")
                lbl_in.get_style_context().add_class("badge")
                lbl_in.get_style_context().add_class("badge-running")
                row.pack_start(lbl_in, False, False, 0)
            else:
                btn_dl = Gtk.Button(label="Descargar")
                btn_dl.get_style_context().add_class("btn-quick")
                btn_dl.get_style_context().add_class("btn-quick-cache")
                btn_dl.connect("clicked", lambda b, mn=m_data["name"]: (dialog.destroy(), self.download_model(mn)))
                row.pack_start(btn_dl, False, False, 0)

            box.pack_start(row, False, False, 0)

        dialog.add_button("Cerrar", Gtk.ResponseType.CLOSE)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    # -------------------------------------------------------------------------
    # Operaciones Ollama (Descarga / Instalación / Arranque)
    # -------------------------------------------------------------------------
    def install_ollama(self):
        cmd = self.client.get_install_command(use_pkexec=True)
        dialog = ProgressDialog(self.main_app, title="Instalar Motor Ollama")
        dialog.set_status("Descargando e instalando Ollama en tu sistema...")

        def task():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t)

                log("⚡ Ejecutando instalador oficial de Ollama en Linux...\n")
                if "pkexec" in cmd:
                    log("ℹ Solicitando autorización de administrador mediante diálogo del sistema (PolicyKit)...\n\n")

                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in iter(p.stdout.readline, ''):
                    log(line)
                p.stdout.close()
                p.wait()

                success = (p.returncode == 0)
                if success:
                    msg = "¡Ollama instalado con éxito en tu sistema!"
                else:
                    msg = "Error al instalar Ollama"
                    log("\n💡 Nota: Si la autorización gráfica fue cancelada o falló, puedes usar el botón 'Instalar en Terminal' para ingresar tu contraseña de sudo directamente en consola.\n")

                GLib.idle_add(dialog.finish, success, msg)
                GLib.idle_add(self.refresh_state)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {ex}")

        threading.Thread(target=task, daemon=True).start()

    def install_ollama_terminal(self):
        cmd_str = "curl -fsSL https://ollama.com/install.sh | sh"
        open_terminal(None, cmd_str)
        GLib.timeout_add(4000, self.refresh_state)

    def start_ollama_service(self):
        def run_start():
            try:
                p = subprocess.run(["systemctl", "start", "ollama"], capture_output=True, text=True)
                if p.returncode != 0:
                    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                try:
                    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            GLib.timeout_add(1500, self.refresh_state)

        threading.Thread(target=run_start, daemon=True).start()

    def download_model(self, model_name: str):
        dialog = ProgressDialog(self.main_app, title=f"Descargando Modelo: {model_name}")
        dialog.set_status(f"Iniciando descarga de {model_name}...")

        def task():
            try:
                def on_progress(pdata):
                    status = pdata.get("status", "")
                    total = pdata.get("total", 0)
                    completed = pdata.get("completed", 0)
                    line_msg = status
                    if total > 0:
                        pct = (completed / total) * 100
                        c_mb = completed / (1024 * 1024)
                        t_mb = total / (1024 * 1024)
                        line_msg = f"{status}: {c_mb:.1f} MB / {t_mb:.1f} MB ({pct:.1f}%)"
                    GLib.idle_add(dialog.append_log, line_msg + "\n")
                    GLib.idle_add(dialog.set_status, line_msg)

                success = self.client.pull_model_stream(model_name, progress_callback=on_progress)
                msg = f"¡Modelo '{model_name}' descargado con éxito!" if success else "Error al descargar el modelo"
                GLib.idle_add(dialog.finish, success, msg)
                GLib.idle_add(self.refresh_state)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {ex}")

        threading.Thread(target=task, daemon=True).start()

    # -------------------------------------------------------------------------
    # Flujo de Chat y Generación Asíncrona
    # -------------------------------------------------------------------------
    def _on_input_key_pressed(self, widget, event):
        # Enter con Ctrl o Enter simple sin Shift
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            is_ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
            is_shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)
            if is_ctrl or not is_shift:
                self.send_message()
                return True
        return False

    def send_message(self):
        if self.is_generating:
            return

        buf = self.text_input.get_buffer()
        start, end = buf.get_bounds()
        text = buf.get_text(start, end, True).strip()
        if not text:
            return

        if not self.active_model:
            self._show_info_dialog("No hay modelo seleccionado", "Por favor selecciona o descarga un modelo antes de preguntar.")
            return

        # Limpiar entrada
        buf.set_text("")

        # Ocultar mensaje de bienvenida si es la primera pregunta
        if hasattr(self, "welcome_widget") and self.welcome_widget.get_parent():
            self.chat_messages_box.remove(self.welcome_widget)

        # 1. Agregar Burbuja de Usuario
        self._add_user_message_ui(text)
        self.messages.append({"role": "user", "content": text})

        # 2. Agregar Burbuja de Asistente (Inicialmente vacía con indicador)
        self._add_assistant_message_ui()

        # 3. Iniciar estado de generación
        self.is_generating = True
        self.cancel_event = threading.Event()
        self.btn_send.set_visible(False)
        self.btn_stop.set_visible(True)
        self.spinner.set_visible(True)
        self.spinner.start()

        # 4. Hilo en segundo plano
        def run_chat_thread():
            system_prompt = (
                "Eres un consultor y asistente técnico de ingeniería de software, arquitectura, sistemas y desarrollo web "
                "integrado de forma nativa en DDEV Studio. Responde siempre en español con explicaciones claras, amigables, "
                "didácticas y con bloques de código bien estructurados."
            )
            if self.chk_context.get_active() and self.active_project_data:
                p = self.active_project_data
                system_prompt += (
                    f"\n\nContexto del proyecto activo en DDEV Studio:\n"
                    f"- Nombre del proyecto: {p.get('name')}\n"
                    f"- Tipo configurado: {p.get('type')}\n"
                    f"- Tecnología detectada: {p.get('_tech_type')}\n"
                    f"- Versión PHP: {p.get('php_version', 'N/A')}\n"
                    f"- Versión Node.js: {p.get('nodejs_version', 'N/A')}\n"
                    f"- Docroot: {p.get('docroot', '')}\n"
                    f"- URL principal: {p.get('primary_url', '')}\n"
                    "Considera este entorno cuando respondas a dudas específicas del proyecto."
                )

            def on_chunk(chunk):
                GLib.idle_add(self._append_chunk, chunk)

            full_resp = self.client.chat_stream(
                self.active_model,
                self.messages,
                system_prompt=system_prompt,
                chunk_callback=on_chunk,
                cancel_event=self.cancel_event
            )
            GLib.idle_add(self._finish_generation, full_resp)

        threading.Thread(target=run_chat_thread, daemon=True).start()

    def _append_chunk(self, chunk):
        if self.current_assistant_label:
            self.current_assistant_text += chunk
            self.current_assistant_label.set_text(self.current_assistant_text)
            self._scroll_chat_to_bottom()

    def _finish_generation(self, full_response):
        self.is_generating = False
        self.btn_send.set_visible(True)
        self.btn_stop.set_visible(False)
        self.spinner.stop()
        self.spinner.set_visible(False)

        if full_response:
            self.messages.append({"role": "assistant", "content": full_response})

        self._scroll_chat_to_bottom()

    def stop_generation(self):
        if self.cancel_event:
            self.cancel_event.set()
        self.is_generating = False
        self.btn_send.set_visible(True)
        self.btn_stop.set_visible(False)
        self.spinner.stop()
        self.spinner.set_visible(False)

    def clear_chat(self):
        self.messages.clear()
        for child in self.chat_messages_box.get_children():
            self.chat_messages_box.remove(child)

        self.welcome_widget = self._build_chat_welcome_widget()
        self.chat_messages_box.pack_start(self.welcome_widget, False, False, 0)
        self.chat_messages_box.show_all()

    # -------------------------------------------------------------------------
    # Renderizado de Burbujas de Conversación
    # -------------------------------------------------------------------------
    def _add_user_message_ui(self, text: str):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.END)

        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bubble.get_style_context().add_class("chat-bubble-user")
        bubble.set_size_request(-1, -1)

        lbl = Gtk.Label(label=text)
        lbl.set_line_wrap(True)
        lbl.set_selectable(True)
        lbl.set_max_width_chars(65)
        lbl.set_xalign(0.0)
        bubble.pack_start(lbl, False, False, 0)

        row.pack_start(bubble, False, False, 0)
        self.chat_messages_box.pack_start(row, False, False, 0)
        self.chat_messages_box.show_all()
        self._scroll_chat_to_bottom()

    def _add_assistant_message_ui(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.START)

        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bubble.get_style_context().add_class("chat-bubble-ai")

        # Cabecera de la burbuja
        h_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        h_row.pack_start(Gtk.Image.new_from_icon_name("help-browser-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_ai_name = Gtk.Label()
        lbl_ai_name.set_markup(f"<b>{self.active_model or 'Asistente IA'}</b>")
        h_row.pack_start(lbl_ai_name, False, False, 0)

        btn_copy = Gtk.Button()
        btn_copy.add(Gtk.Image.new_from_icon_name("edit-copy-symbolic", Gtk.IconSize.MENU))
        btn_copy.get_style_context().add_class("btn-quick")
        btn_copy.set_tooltip_text("Copiar respuesta al portapapeles")
        btn_copy.connect("clicked", lambda b: self._copy_current_assistant_text())
        h_row.pack_end(btn_copy, False, False, 0)
        bubble.pack_start(h_row, False, False, 0)

        self.current_assistant_text = ""
        self.current_assistant_label = Gtk.Label(label="Pensando...")
        self.current_assistant_label.set_line_wrap(True)
        self.current_assistant_label.set_selectable(True)
        self.current_assistant_label.set_max_width_chars(80)
        self.current_assistant_label.set_xalign(0.0)
        bubble.pack_start(self.current_assistant_label, False, False, 0)

        row.pack_start(bubble, False, False, 0)
        self.chat_messages_box.pack_start(row, False, False, 0)
        self.chat_messages_box.show_all()
        self._scroll_chat_to_bottom()

    def _copy_current_assistant_text(self):
        if self.current_assistant_text:
            clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clip.set_text(self.current_assistant_text, -1)
            clip.store()

    def _scroll_chat_to_bottom(self):
        adj = self.chat_scrolled.get_vadjustment()
        GLib.idle_add(lambda: adj.set_value(adj.get_upper() - adj.get_page_size()))

    def _show_info_dialog(self, title, message):
        d = Gtk.MessageDialog(
            transient_for=self.main_app,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        d.format_secondary_text(message)
        d.run()
        d.destroy()
