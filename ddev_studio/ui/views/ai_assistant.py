# -*- coding: utf-8 -*-
"""
Vista del Asistente de IA Local y Centro de Consultas para DDEV Studio.
Módulo completamente desacoplado basado en Ollama (privado, offline y local).
"""

import os
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
    read_context_file,
    find_and_read_project_doc,
    SUPPORTED_TEXT_EXTENSIONS,
)
from ddev_studio.core.terminal import open_terminal
from ddev_studio.core.voice import VoiceManager
from ddev_studio.ui.dialogs.progress import ProgressDialog
from ddev_studio.ui.dialogs.voice_settings import VoiceSettingsDialog


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
        self.attached_files = []
        self.external_projects = []
        self.current_assistant_bubble = None
        self.current_assistant_label = None
        self.current_assistant_text = ""
        self.current_loading_box = None
        self.loading_title_label = None
        self.loading_desc_label = None
        self.loading_progress_bar = None
        self.pulse_timer_id = None
        self.loading_elapsed_seconds = 0
        self.loading_ticks = 0
        self.is_cold_start = True

        self.voice_mgr = VoiceManager()
        self.is_recording_mic = False
        self._active_speaking_img = None
        self._active_speaking_btn = None

        self.connect("destroy", lambda w: (
            self._stop_loading_indicator(),
            self.voice_mgr.stop_playback(),
            self.voice_mgr.stop_recording(),
            self.voice_mgr.unload_daemon()
        ))

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

        # Indicador de Consumo de RAM del modelo
        self.lbl_memory = Gtk.Label()
        self.lbl_memory.get_style_context().add_class("badge")
        self.lbl_memory.set_no_show_all(True)
        self.lbl_memory.set_visible(False)
        self.top_bar.pack_start(self.lbl_memory, False, False, 0)

        # Botón Liberar Memoria RAM
        self.btn_unload_memory = Gtk.Button()
        b_un = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.img_unload = Gtk.Image.new_from_icon_name("process-stop-symbolic", Gtk.IconSize.MENU)
        b_un.pack_start(self.img_unload, False, False, 0)
        self.lbl_unload_text = Gtk.Label(label="Liberar RAM")
        b_un.pack_start(self.lbl_unload_text, False, False, 0)
        b_un.show_all()
        self.btn_unload_memory.add(b_un)
        self.btn_unload_memory.get_style_context().add_class("btn-quick")
        self.btn_unload_memory.get_style_context().add_class("btn-quick-uninstall")
        self.btn_unload_memory.set_tooltip_text("Cancelar proceso y descargar el modelo de la memoria RAM inmediatamente para liberar CPU y recursos")
        self.btn_unload_memory.connect("clicked", lambda b: self.unload_active_model())
        self.btn_unload_memory.set_no_show_all(True)
        self.btn_unload_memory.set_visible(False)
        self.top_bar.pack_start(self.btn_unload_memory, False, False, 0)

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

        # Botón Ayuda / Manual de Contexto
        self.btn_context_help = Gtk.Button()
        self.btn_context_help.add(Gtk.Image.new_from_icon_name("help-about-symbolic", Gtk.IconSize.MENU))
        self.btn_context_help.get_style_context().add_class("btn-quick")
        self.btn_context_help.set_tooltip_text("Manual de uso: ¿Qué hace el contexto de proyecto y cómo usarlo?")
        self.btn_context_help.connect("clicked", lambda b: self._show_context_help_dialog())
        self.top_bar.pack_start(self.btn_context_help, False, False, 0)

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

        # Botón Configuración de Voz (Whisper + Kokoro)
        self.btn_voice = Gtk.Button()
        b_vc = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.img_voice_top = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.MENU)
        b_vc.pack_start(self.img_voice_top, False, False, 0)
        self.lbl_voice_btn = Gtk.Label(label="Voz")
        b_vc.pack_start(self.lbl_voice_btn, False, False, 0)
        self.btn_voice.add(b_vc)
        self.btn_voice.get_style_context().add_class("btn-quick")
        self.btn_voice.set_tooltip_text("Configuración y estado de Voz (Whisper STT & Kokoro TTS)")
        self.btn_voice.connect("clicked", lambda b: self._show_voice_settings_dialog())
        self.top_bar.pack_start(self.btn_voice, False, False, 0)

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

        # Contenedor de chips de archivos adjuntos (horizontal desplazable)
        self.attachments_scrolled = Gtk.ScrolledWindow()
        self.attachments_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.attachments_scrolled.set_min_content_height(32)
        self.attachments_scrolled.set_no_show_all(True)
        self.attachments_scrolled.set_visible(False)

        self.attachments_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.attachments_box.set_margin_start(8)
        self.attachments_box.set_margin_end(8)
        self.attachments_box.set_margin_top(4)
        self.attachments_box.set_margin_bottom(2)
        self.attachments_scrolled.add(self.attachments_box)
        input_container.pack_start(self.attachments_scrolled, False, False, 0)

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

        # Botón para adjuntar archivo (El Clip 📎)
        self.btn_attach = Gtk.Button()
        self.btn_attach.add(Gtk.Image.new_from_icon_name("mail-attachment-symbolic", Gtk.IconSize.BUTTON))
        self.btn_attach.get_style_context().add_class("btn-quick")
        self.btn_attach.set_valign(Gtk.Align.CENTER)
        self.btn_attach.set_tooltip_text("Adjuntar archivo de código, Markdown (.md) o log como contexto para la IA")
        self.btn_attach.connect("clicked", lambda b: self._on_attach_file_clicked())
        input_row.pack_start(self.btn_attach, False, False, 0)

        # Botón Dictar por Micrófono (Whisper STT)
        self.btn_mic = Gtk.Button()
        self.img_mic = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic", Gtk.IconSize.BUTTON)
        self.btn_mic.add(self.img_mic)
        self.btn_mic.get_style_context().add_class("btn-quick")
        self.btn_mic.set_valign(Gtk.Align.CENTER)
        self.btn_mic.set_tooltip_text("Dictar por voz con Whisper (Español)")
        self.btn_mic.connect("clicked", lambda b: self._on_mic_button_clicked())
        input_row.pack_start(self.btn_mic, False, False, 0)

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
            running_info = self.client.get_running_models_info() if is_running else []

            def update_ui():
                self.installed_models = models
                self._update_memory_ui(running_info)

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

                    # Actualizar combo de modelos solo si la lista ha cambiado
                    new_names = [m["name"] for m in models]
                    if getattr(self, "_cached_model_names", None) != new_names:
                        self._cached_model_names = new_names
                        target_sel = self.active_model or self.combo_models.get_active_text()
                        self.combo_models.handler_block_by_func(self._on_model_changed)
                        self.combo_models.remove_all()
                        for name in new_names:
                            self.combo_models.append(name, name)
                        if new_names:
                            if target_sel and target_sel in new_names:
                                self.combo_models.set_active_id(target_sel)
                            else:
                                self.combo_models.set_active(0)
                            self.active_model = self.combo_models.get_active_text() or ""
                        self.combo_models.handler_unblock_by_func(self._on_model_changed)
                    else:
                        # Si ya está poblado, asegurar que la selección persista si se deseleccionó
                        if self.active_model and not self.combo_models.get_active_text():
                            self.combo_models.set_active_id(self.active_model)

                self.populate_projects()

            GLib.idle_add(update_ui)

        threading.Thread(target=task, daemon=True).start()

    def _update_memory_ui(self, running_info: list[dict]):
        if not hasattr(self, "lbl_memory") or not hasattr(self, "btn_unload_memory"):
            return
        if running_info:
            first_m = running_info[0]
            m_name = first_m.get("name", "")
            size_str = first_m.get("size_str", "")
            ctx = self.lbl_memory.get_style_context()
            ctx.remove_class("badge-stopped")
            if not ctx.has_class("badge-running"):
                ctx.add_class("badge-running")
            self.lbl_memory.set_markup(f"🧠 <b>RAM: {size_str}</b>")
            self.lbl_memory.set_tooltip_text(
                f"Modelo '{m_name}' residente en memoria ({size_str}).\n"
                "Responderá al instante a tus preguntas."
            )
            self.lbl_memory.set_visible(True)
            self.btn_unload_memory.set_tooltip_text(
                f"Cancelar y descargar '{m_name}' de la memoria para liberar {size_str} de RAM y CPU"
            )
            child = self.btn_unload_memory.get_child()
            if child:
                child.show_all()
            self.btn_unload_memory.set_visible(True)
        else:
            ctx = self.lbl_memory.get_style_context()
            ctx.remove_class("badge-running")
            if not ctx.has_class("badge-stopped"):
                ctx.add_class("badge-stopped")
            self.lbl_memory.set_markup("<small>En reposo (0 MB RAM)</small>")
            self.lbl_memory.set_tooltip_text("No hay ningún modelo cargado en memoria RAM en este momento.")
            self.lbl_memory.set_visible(True)
            self.btn_unload_memory.set_visible(False)

    def unload_active_model(self):
        """Descarga todos los modelos cargados en memoria RAM para liberar CPU y recursos del sistema."""
        self.btn_unload_memory.set_sensitive(False)
        self.lbl_unload_text.set_text("Liberando...")

        def task():
            try:
                running = self.client.get_running_models()
                for m in running:
                    self.client.unload_model(m)
                self.voice_mgr.unload_daemon()
            finally:
                def restore():
                    self.lbl_unload_text.set_text("Liberar RAM")
                    self.btn_unload_memory.set_sensitive(True)
                    self.refresh_state()
                GLib.idle_add(restore)

        threading.Thread(target=task, daemon=True).start()

    def populate_projects(self, projects=None):
        """Llena la lista de proyectos conocidos para la opción de contexto."""
        if projects is None:
            projects = getattr(self.main_app, "projects_cache", [])

        all_projects = list(projects)
        for ext_p in getattr(self, "external_projects", []):
            if not any(p.get("name") == ext_p.get("name") for p in all_projects):
                all_projects.append(ext_p)

        self._cached_projects_data = all_projects
        pnames = [p.get("name", "") for p in all_projects if p.get("name")]

        cur = self.combo_projects.get_active_id()
        self.combo_projects.handler_block_by_func(self._on_project_changed)
        self.combo_projects.remove_all()
        for p in all_projects:
            pname = p.get("name", "")
            if pname:
                display = f"📁 {pname} (Externo)" if p.get("is_external") else pname
                self.combo_projects.append(pname, display)

        # Opción para seleccionar otra carpeta o repositorio libre
        self.combo_projects.append("__browse_external__", "➕ Explorar otra carpeta o repositorio...")

        if pnames:
            if cur and cur in pnames:
                self.combo_projects.set_active_id(cur)
            else:
                self.combo_projects.set_active_id(pnames[0])
        self.combo_projects.handler_unblock_by_func(self._on_project_changed)
        self._on_project_changed(self.combo_projects)

    def _on_model_changed(self, combo):
        txt = combo.get_active_text()
        if txt:
            self.active_model = txt

    def _on_context_toggled(self, chk):
        active = chk.get_active()
        self.combo_projects.set_sensitive(active)
        if active and self.combo_projects.get_active() < 0:
            if self.combo_projects.get_model() and len(self.combo_projects.get_model()) > 0:
                self.combo_projects.set_active(0)
        self._on_project_changed(self.combo_projects)

    def _on_project_changed(self, combo):
        active_id = combo.get_active_id()
        if active_id == "__browse_external__":
            GLib.idle_add(self._choose_external_folder)
            return

        projects = getattr(self, "_cached_projects_data", []) or getattr(self.main_app, "projects_cache", [])
        self.active_project_data = next((p for p in projects if p.get("name") == active_id), {})

    def _choose_external_folder(self):
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar carpeta o repositorio para el contexto",
            transient_for=self.main_app,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Seleccionar", Gtk.ResponseType.ACCEPT)

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            folder = dialog.get_filename()
            dialog.destroy()
            if folder and os.path.isdir(folder):
                self._add_external_project(folder)
        else:
            dialog.destroy()
            if self.active_project_data and self.active_project_data.get("name"):
                self.combo_projects.set_active_id(self.active_project_data["name"])
            elif getattr(self, "_cached_projects_data", []):
                first_name = self._cached_projects_data[0].get("name")
                if first_name:
                    self.combo_projects.set_active_id(first_name)

    def _add_external_project(self, folder: str):
        from ddev_studio.core.detector import detect_project_details
        details = detect_project_details(folder)
        pname = os.path.basename(folder.rstrip("/"))
        ext_project = {
            "name": pname,
            "approot": folder,
            "dir": folder,
            "type": details.get("type", "external"),
            "_tech_type": details.get("type", "Proyecto Externo"),
            "php_version": details.get("php", "N/A"),
            "nodejs_version": details.get("nodejs", "N/A"),
            "docroot": details.get("docroot", "."),
            "primary_url": f"file://{folder}",
            "is_external": True,
        }
        if not hasattr(self, "external_projects"):
            self.external_projects = []
        self.external_projects = [p for p in self.external_projects if p.get("approot") != folder]
        self.external_projects.append(ext_project)

        self.populate_projects()
        self.combo_projects.set_active_id(pname)

    # -------------------------------------------------------------------------
    # Manejo de Archivos Adjuntos (El Clip 📎)
    # -------------------------------------------------------------------------
    def _on_attach_file_clicked(self):
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar archivo para adjuntar al contexto",
            transient_for=self.main_app,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Adjuntar", Gtk.ResponseType.ACCEPT)

        # Filtros de selección de archivos
        filter_supported = Gtk.FileFilter()
        filter_supported.set_name("Archivos soportados (Código, Markdown, Logs)")
        for ext in sorted(SUPPORTED_TEXT_EXTENSIONS):
            filter_supported.add_pattern(f"*{ext}")
            filter_supported.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(filter_supported)

        filter_md = Gtk.FileFilter()
        filter_md.set_name("Archivos Markdown (*.md, *.markdown)")
        filter_md.add_pattern("*.md")
        filter_md.add_pattern("*.MD")
        filter_md.add_pattern("*.markdown")
        filter_md.add_pattern("*.MARKDOWN")
        dialog.add_filter(filter_md)

        filter_code = Gtk.FileFilter()
        filter_code.set_name("Código fuente (*.py, *.php, *.js, *.ts, *.json, *.yaml, *.sql)")
        for ext in [".py", ".php", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".html", ".css", ".sql", ".sh"]:
            filter_code.add_pattern(f"*{ext}")
            filter_code.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(filter_code)

        filter_logs = Gtk.FileFilter()
        filter_logs.set_name("Archivos de Registro / Logs (*.log, *.txt)")
        filter_logs.add_pattern("*.log")
        filter_logs.add_pattern("*.LOG")
        filter_logs.add_pattern("*.txt")
        filter_logs.add_pattern("*.TXT")
        dialog.add_filter(filter_logs)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("Todos los archivos (*)")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            dialog.destroy()
            if filename:
                self._attach_file(filename)
        else:
            dialog.destroy()

    def _attach_file(self, filepath: str):
        if any(f.get("path") == filepath for f in self.attached_files):
            self._show_info_dialog("Archivo ya adjuntado", f"El archivo '{os.path.basename(filepath)}' ya está adjunto.")
            return

        try:
            file_data = read_context_file(filepath)
        except Exception as ex:
            self._show_info_dialog("Error al leer archivo", f"No se pudo leer el archivo seleccionado:\n{ex}")
            return

        self.attached_files.append(file_data)
        self._add_attachment_chip(file_data)

        if file_data.get("truncated"):
            self._show_info_dialog(
                "Archivo truncado por seguridad de CPU",
                f"El archivo '{file_data['name']}' supera los 30 KB.\n\n"
                "Para proteger la memoria RAM y evitar congelar la inferencia en CPU de Ollama, "
                "se ha incluido de forma segura el primer fragmento de 30 KB (~500 a 800 líneas de código)."
            )

    def _add_attachment_chip(self, file_data: dict):
        chip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        chip.get_style_context().add_class("chat-attachment-chip")

        icon_name = "text-x-generic-symbolic"
        name_lower = file_data["name"].lower()
        if name_lower.endswith(".md") or name_lower.endswith(".markdown"):
            icon_name = "x-office-document-symbolic"
        elif any(name_lower.endswith(ext) for ext in [".py", ".php", ".js", ".ts", ".jsx", ".tsx", ".sh"]):
            icon_name = "text-x-script-symbolic"
        elif name_lower.endswith(".log"):
            icon_name = "utilities-terminal-symbolic"

        img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        chip.pack_start(img, False, False, 0)

        lbl = Gtk.Label()
        lbl.set_markup(f"<b>{file_data['name']}</b> <small>({file_data['size_str']})</small>")
        chip.pack_start(lbl, False, False, 0)

        btn_remove = Gtk.Button()
        btn_remove.add(Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU))
        btn_remove.get_style_context().add_class("btn-chip-remove")
        btn_remove.set_tooltip_text("Quitar archivo adjunto")
        btn_remove.connect("clicked", lambda b, c=chip, fd=file_data: self._remove_attachment(c, fd))
        chip.pack_start(btn_remove, False, False, 0)

        chip.show_all()
        self.attachments_box.pack_start(chip, False, False, 0)
        self.attachments_scrolled.set_visible(True)
        self.attachments_scrolled.show_all()

    def _remove_attachment(self, chip_widget, file_data):
        if file_data in self.attached_files:
            self.attached_files.remove(file_data)
        self.attachments_box.remove(chip_widget)
        if not self.attached_files:
            self.attachments_scrolled.set_visible(False)

    def _use_suggestion(self, text):
        buf = self.text_input.get_buffer()
        buf.set_text(text)
        self.send_message()

    def _show_context_help_dialog(self):
        """Muestra un diálogo modal interactivo que sirve como guía y manual completo de contexto para la IA."""
        dialog = Gtk.Dialog(
            title="Manual y Guía de Contexto del Asistente IA",
            transient_for=self.main_app,
            modal=True,
        )
        dialog.set_default_size(620, 560)
        box = dialog.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(16)
        box.set_margin_bottom(16)

        # Encabezado con icono y título
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        img_info = Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.DIALOG)
        header_box.pack_start(img_info, False, False, 0)

        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_h = Gtk.Label()
        lbl_h.set_markup("<b><big>Guía Maestra: Contexto, Adjuntos y Proyectos</big></b>")
        lbl_h.set_halign(Gtk.Align.START)
        title_vbox.pack_start(lbl_h, False, False, 0)

        lbl_sub = Gtk.Label(label="Aprende a alimentar al asistente con código, Markdown, logs y arquitectura real")
        lbl_sub.set_halign(Gtk.Align.START)
        title_vbox.pack_start(lbl_sub, False, False, 0)
        header_box.pack_start(title_vbox, True, True, 0)
        box.pack_start(header_box, False, False, 0)

        # Scrolled window para el contenido
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Sección 1: ¿Qué información recibe la IA?
        card1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card1.get_style_context().add_class("option-highlight-box")
        lbl_t1 = Gtk.Label()
        lbl_t1.set_markup("<b>1. Ficha Técnica del Entorno (System Prompt)</b>")
        lbl_t1.set_halign(Gtk.Align.START)
        card1.pack_start(lbl_t1, False, False, 0)

        lbl_d1 = Gtk.Label()
        lbl_d1.set_markup(
            "Al marcar la casilla <b>'Incluir contexto de:'</b>, DDEV Studio inyecta automáticamente la ficha "
            "técnica del proyecto seleccionado como instrucción base:\n\n"
            "• <b>Framework / Stack:</b> Drupal 11/10/7, Django, Laravel, Symfony, Next.js, n8n, OpenClaw, etc.\n"
            "• <b>Versiones activas:</b> Versión exacta de PHP (ej. 8.3) y Node.js (ej. 24.22.1 / 22).\n"
            "• <b>Estructura:</b> Directorio raíz (docroot) y URL local HTTPS (https://...ddev.site)."
        )
        lbl_d1.set_line_wrap(True)
        lbl_d1.set_halign(Gtk.Align.START)
        card1.pack_start(lbl_d1, False, False, 0)
        content_box.pack_start(card1, False, False, 0)

        # Sección 2: El Clip de Adjuntar Archivos
        card2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card2.get_style_context().add_class("module-item-box")
        lbl_t2 = Gtk.Label()
        lbl_t2.set_markup("<b>2. Botón de Adjuntar Archivo (El Clip 📎)</b>")
        lbl_t2.set_halign(Gtk.Align.START)
        card2.pack_start(lbl_t2, False, False, 0)

        lbl_d2 = Gtk.Label()
        lbl_d2.set_markup(
            "Junto a la caja de texto encontrarás el icono de clip. Puedes adjuntar cualquier archivo de texto para que la IA lo analice:\n\n"
            "• 📄 <b>Archivos Markdown (.md, .markdown):</b> Especificaciones técnicas, planes de trabajo o notas.\n"
            "• 💻 <b>Código Fuente (.py, .js, .ts, .php, .html, .css, .json, .yaml, .sql):</b> Solicita refactorización, explicaciones de algoritmos o resolución de bugs.\n"
            "• 📋 <b>Logs de error (.log, .txt):</b> Pega trazas de error de terminal, logs de Apache/Nginx o Docker para diagnóstico de fallos.\n"
            "• 🛡️ <b>Límite Protector de 30 KB:</b> Para evitar congelar tu procesador o saturar la memoria RAM en CPU, los archivos se truncan de forma segura a 30 KB (~500 a 800 líneas de código)."
        )
        lbl_d2.set_line_wrap(True)
        lbl_d2.set_halign(Gtk.Align.START)
        card2.pack_start(lbl_d2, False, False, 0)
        content_box.pack_start(card2, False, False, 0)

        # Sección 3: Lectura Automática de Documentación (README / PROJECT_CONTEXT)
        card3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card3.get_style_context().add_class("module-item-box")
        lbl_t3 = Gtk.Label()
        lbl_t3.set_markup("<b>3. Inyección Automática de README.md o PROJECT_CONTEXT.md</b>")
        lbl_t3.set_halign(Gtk.Align.START)
        card3.pack_start(lbl_t3, False, False, 0)

        lbl_d3 = Gtk.Label()
        lbl_d3.set_markup(
            "Si tu proyecto contiene un archivo <code>PROJECT_CONTEXT.md</code> o <code>README.md</code> en su directorio raíz, "
            "el Asistente lo detecta y lo lee automáticamente al marcar el contexto. De esta manera, el modelo conoce "
            "la arquitectura, convenciones y módulos de tu proyecto sin que tengas que copiarlos a mano."
        )
        lbl_d3.set_line_wrap(True)
        lbl_d3.set_halign(Gtk.Align.START)
        card3.pack_start(lbl_d3, False, False, 0)
        content_box.pack_start(card3, False, False, 0)

        # Sección 4: Modo Carpeta Libre / Proyectos Externos
        card4 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card4.get_style_context().add_class("module-item-box")
        lbl_t4 = Gtk.Label()
        lbl_t4.set_markup("<b>4. Modo Carpeta Libre (Proyectos Fuera de DDEV)</b>")
        lbl_t4.set_halign(Gtk.Align.START)
        card4.pack_start(lbl_t4, False, False, 0)

        lbl_d4 = Gtk.Label()
        lbl_d4.set_markup(
            "En el menú desplegable de proyectos puedes elegir <b>'➕ Explorar otra carpeta o repositorio...'</b>. "
            "Esto te permite seleccionar cualquier repositorio clonado o carpeta de código de tu equipo, "
            "sin necesidad de que esté contenerizado o configurado con DDEV."
        )
        lbl_d4.set_line_wrap(True)
        lbl_d4.set_halign(Gtk.Align.START)
        card4.pack_start(lbl_d4, False, False, 0)
        content_box.pack_start(card4, False, False, 0)

        # Sección 5: Recomendaciones y Buenas Prácticas
        card5 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card5.get_style_context().add_class("option-highlight-box")
        lbl_t5 = Gtk.Label()
        lbl_t5.set_markup("<b>5. Recomendaciones de Rendimiento y Memoria</b>")
        lbl_t5.set_halign(Gtk.Align.START)
        card5.pack_start(lbl_t5, False, False, 0)

        lbl_d5 = Gtk.Label()
        lbl_d5.set_markup(
            "• 🧠 <b>Monitorea la Memoria:</b> En la barra superior puedes observar cuánta memoria RAM consume el modelo en tiempo real.\n"
            "• 🛑 <b>Botón 'Liberar RAM':</b> Cuando termines tus consultas, pulsa el botón rojo para descargar el modelo de memoria inmediatamente.\n"
            "• ⌨️ <b>Atajo Rápido:</b> Puedes enviar tus consultas pulsando <code>Ctrl + Enter</code> desde el cuadro de texto multilínea."
        )
        lbl_d5.set_line_wrap(True)
        lbl_d5.set_halign(Gtk.Align.START)
        card5.pack_start(lbl_d5, False, False, 0)
        content_box.pack_start(card5, False, False, 0)

        scrolled.add(content_box)
        box.pack_start(scrolled, True, True, 0)

        dialog.add_button("Cerrar Manual", Gtk.ResponseType.CLOSE)
        dialog.show_all()
        dialog.run()
        dialog.destroy()


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

        # Capturar archivos adjuntos actuales y limpiar barra visual
        current_attachments = list(self.attached_files)
        self.attached_files.clear()
        for ch in self.attachments_box.get_children():
            self.attachments_box.remove(ch)
        self.attachments_scrolled.set_visible(False)

        # Ocultar mensaje de bienvenida si es la primera pregunta
        if hasattr(self, "welcome_widget") and self.welcome_widget.get_parent():
            self.chat_messages_box.remove(self.welcome_widget)

        # 1. Agregar Burbuja de Usuario
        self._add_user_message_ui(text, attached_files=current_attachments)

        # Formatear archivos adjuntos para el prompt de Ollama
        user_content = text
        if current_attachments:
            attach_blocks = []
            for af in current_attachments:
                name = af.get("name", "archivo")
                ext = os.path.splitext(name)[1].lstrip(".").lower() or "text"
                trunc_txt = " [Fragmento truncado a 30 KB por seguridad de CPU]" if af.get("truncated") else ""
                attach_blocks.append(
                    f"### Archivo adjunto: {name} ({af.get('size_str', '')}){trunc_txt}\n"
                    f"```{ext}\n{af.get('content', '')}\n```"
                )
            user_content = f"{text}\n\n" + "\n\n".join(attach_blocks)

        self.messages.append({"role": "user", "content": user_content})

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
            # Comprobación de estado en memoria (Warm vs Cold Start)
            is_loaded = self.client.is_model_loaded(self.active_model)
            GLib.idle_add(self._update_loading_mode, is_loaded)

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

                # Inyección automática de documentación README.md o PROJECT_CONTEXT.md
                approot = p.get("approot") or p.get("dir")
                if approot and os.path.isdir(approot):
                    doc = find_and_read_project_doc(approot)
                    if doc:
                        trunc_note = " (resumen inicial)" if doc.get("truncated") else ""
                        system_prompt += (
                            f"\n\nDocumentación del proyecto ({doc['name']}{trunc_note}):\n"
                            f"```markdown\n{doc['content']}\n```"
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
        if self.current_loading_box:
            self._stop_loading_indicator()

        if self.current_assistant_label:
            if not self.current_assistant_label.get_visible():
                self.current_assistant_label.set_visible(True)
            self.current_assistant_text += chunk
            self.current_assistant_label.set_text(self.current_assistant_text)
            self._scroll_chat_to_bottom()

    def _finish_generation(self, full_response):
        self._stop_loading_indicator()

        self.is_generating = False
        self.btn_send.set_visible(True)
        self.btn_stop.set_visible(False)
        self.spinner.stop()
        self.spinner.set_visible(False)

        if self.current_assistant_label:
            if not self.current_assistant_label.get_visible():
                self.current_assistant_label.set_visible(True)
            if not self.current_assistant_text and full_response:
                self.current_assistant_text = full_response
                self.current_assistant_label.set_text(full_response)

        if full_response:
            self.messages.append({"role": "assistant", "content": full_response})
            if self.current_assistant_bubble:
                self.current_assistant_bubble._raw_text = full_response

            # Auto-lectura si está activada en preferencias de voz
            if self.voice_mgr.is_installed():
                cfg = self.voice_mgr.get_config()
                if cfg.get("auto_speak"):
                    bubble = self.current_assistant_bubble
                    if bubble and hasattr(bubble, "_btn_speak") and hasattr(bubble, "_img_speak"):
                        self._speak_bubble_text(bubble, bubble._btn_speak, bubble._img_speak)

        self._scroll_chat_to_bottom()
        GLib.timeout_add(800, self.refresh_state)

    def stop_generation(self):
        if self.cancel_event:
            self.cancel_event.set()
        self._stop_loading_indicator()
        self.is_generating = False
        self.btn_send.set_visible(True)
        self.btn_stop.set_visible(False)
        self.spinner.stop()
        self.spinner.set_visible(False)
        if self.current_assistant_label and not self.current_assistant_label.get_visible():
            self.current_assistant_label.set_text("(Generación cancelada por el usuario)")
            self.current_assistant_label.set_visible(True)

    def clear_chat(self):
        self._stop_loading_indicator()
        self.messages.clear()
        for child in self.chat_messages_box.get_children():
            self.chat_messages_box.remove(child)

        self.welcome_widget = self._build_chat_welcome_widget()
        self.chat_messages_box.pack_start(self.welcome_widget, False, False, 0)
        self.chat_messages_box.show_all()

    # -------------------------------------------------------------------------
    # Renderizado de Burbujas de Conversación
    # -------------------------------------------------------------------------
    def _add_user_message_ui(self, text: str, attached_files: list = None):
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

        if attached_files:
            chips_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            chips_box.set_margin_top(4)
            for af in attached_files:
                pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                pill.get_style_context().add_class("chat-attachment-chip")
                pill.pack_start(Gtk.Image.new_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.MENU), False, False, 0)
                pill_lbl = Gtk.Label()
                pill_lbl.set_markup(f"<small>{af['name']} ({af['size_str']})</small>")
                pill.pack_start(pill_lbl, False, False, 0)
                chips_box.pack_start(pill, False, False, 0)
            bubble.pack_start(chips_box, False, False, 0)

        row.pack_start(bubble, False, False, 0)
        self.chat_messages_box.pack_start(row, False, False, 0)
        self.chat_messages_box.show_all()
        self._scroll_chat_to_bottom()

    def _add_assistant_message_ui(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.START)

        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bubble.get_style_context().add_class("chat-bubble-ai")
        self.current_assistant_bubble = bubble

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

        # Botón Escuchar respuesta con voz (Kokoro TTS)
        btn_speak = Gtk.Button()
        img_speak = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.MENU)
        btn_speak.add(img_speak)
        btn_speak.get_style_context().add_class("btn-quick")
        btn_speak.set_tooltip_text("Escuchar respuesta en voz alta (Kokoro TTS)")
        btn_speak.connect("clicked", lambda b: self._speak_bubble_text(bubble, btn_speak, img_speak))
        h_row.pack_end(btn_speak, False, False, 0)

        bubble._btn_speak = btn_speak
        bubble._img_speak = img_speak
        bubble._raw_text = ""
        bubble.pack_start(h_row, False, False, 0)

        # Iniciar contenedor visual de carga con barra animada
        self._start_loading_indicator(bubble)

        # Label para texto generado (inicialmente oculto mientras carga)
        self.current_assistant_text = ""
        self.current_assistant_label = Gtk.Label(label="")
        self.current_assistant_label.set_line_wrap(True)
        self.current_assistant_label.set_selectable(True)
        self.current_assistant_label.set_max_width_chars(80)
        self.current_assistant_label.set_xalign(0.0)
        self.current_assistant_label.set_no_show_all(True)
        self.current_assistant_label.set_visible(False)
        bubble.pack_start(self.current_assistant_label, False, False, 0)

        row.pack_start(bubble, False, False, 0)
        self.chat_messages_box.pack_start(row, False, False, 0)
        self.chat_messages_box.show_all()
        self._scroll_chat_to_bottom()

    def _start_loading_indicator(self, bubble):
        self._stop_loading_indicator()

        self.loading_elapsed_seconds = 0
        self.loading_ticks = 0
        self.is_cold_start = True

        load_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        load_box.get_style_context().add_class("chat-loader-box")
        self.current_loading_box = load_box

        # Título
        self.loading_title_label = Gtk.Label()
        self.loading_title_label.set_markup("<b>🧠 Cargando modelo en memoria RAM/VRAM...</b>")
        self.loading_title_label.set_halign(Gtk.Align.START)
        load_box.pack_start(self.loading_title_label, False, False, 0)

        # Barra de progreso activa en modo pulse
        self.loading_progress_bar = Gtk.ProgressBar()
        self.loading_progress_bar.set_pulse_step(0.06)
        load_box.pack_start(self.loading_progress_bar, False, False, 0)

        # Subtítulo descriptivo con cronómetro dinámico
        self.loading_desc_label = Gtk.Label()
        self.loading_desc_label.set_markup(
            f"<small>Cargando modelo <b>{self.active_model}</b> por primera vez a la memoria RAM...\n"
            f"Tiempo transcurrido: <b>0s</b> (en CPU puede tomar alrededor de 1 minuto).\n"
            f"Una vez cargado, permanecerá en memoria y responderá al instante.</small>"
        )
        self.loading_desc_label.set_line_wrap(True)
        self.loading_desc_label.set_halign(Gtk.Align.START)
        self.loading_desc_label.set_max_width_chars(75)
        load_box.pack_start(self.loading_desc_label, False, False, 0)

        bubble.pack_start(load_box, False, False, 0)

        # Iniciar ciclo de animación cada 100ms
        self.pulse_timer_id = GLib.timeout_add(100, self._on_loading_tick)

    def _on_loading_tick(self):
        if not self.is_generating or not self.current_loading_box:
            self.pulse_timer_id = None
            return False

        if self.loading_progress_bar:
            self.loading_progress_bar.pulse()

        self.loading_ticks += 1
        if self.loading_ticks % 10 == 0:
            self.loading_elapsed_seconds += 1
            sec = self.loading_elapsed_seconds
            if self.loading_desc_label:
                if self.is_cold_start:
                    self.loading_desc_label.set_markup(
                        f"<small>Primer uso: cargando archivos de <b>{self.active_model}</b> en memoria RAM.\n"
                        f"Tiempo transcurrido: <b>{sec}s</b>. Una vez cargado, las siguientes preguntas responderán al instante.</small>"
                    )
                else:
                    self.loading_desc_label.set_markup(
                        f"<small>Modelo activo en memoria RAM. Generando respuesta...\n"
                        f"Tiempo transcurrido: <b>{sec}s</b>.</small>"
                    )
        return True

    def _update_loading_mode(self, is_loaded: bool):
        self.is_cold_start = not is_loaded
        if not self.current_loading_box:
            return
        if is_loaded:
            if self.loading_title_label:
                self.loading_title_label.set_markup("<b>💭 Generando respuesta...</b>")
            if self.loading_desc_label:
                self.loading_desc_label.set_markup(
                    f"<small>Modelo activo en memoria RAM. Generando tokens...\n"
                    f"Tiempo transcurrido: <b>{self.loading_elapsed_seconds}s</b>.</small>"
                )
        else:
            if self.loading_title_label:
                self.loading_title_label.set_markup("<b>🧠 Cargando modelo en memoria RAM/VRAM por primera vez...</b>")

    def _stop_loading_indicator(self):
        if self.pulse_timer_id is not None:
            GLib.source_remove(self.pulse_timer_id)
            self.pulse_timer_id = None

        if self.current_loading_box:
            parent = self.current_loading_box.get_parent()
            if parent:
                parent.remove(self.current_loading_box)
            self.current_loading_box = None
            self.loading_progress_bar = None
            self.loading_title_label = None
            self.loading_desc_label = None

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

    # -------------------------------------------------------------------------
    # Integración de Voz (Whisper STT y Kokoro TTS)
    # -------------------------------------------------------------------------
    def _show_voice_settings_dialog(self):
        dialog = VoiceSettingsDialog(self.main_app, on_changed_callback=self._on_voice_settings_changed)
        dialog.run()
        dialog.destroy()

    def _on_voice_settings_changed(self):
        pass

    def _on_mic_button_clicked(self):
        if not self.voice_mgr.is_installed():
            self._show_voice_settings_dialog()
            return

        if not self.is_recording_mic:
            # Iniciar captura de audio
            try:
                self.voice_mgr.start_recording()
                self.is_recording_mic = True
                self.btn_mic.get_style_context().add_class("btn-recording")
                self.img_mic.set_from_icon_name("media-record-symbolic", Gtk.IconSize.BUTTON)
                self.btn_mic.set_tooltip_text("Grabando tu voz... Haz clic aquí para detener y transcribir con Whisper")
            except Exception as ex:
                self._show_info_dialog("Error al iniciar micrófono", str(ex))
        else:
            # Detener y transcribir
            self.is_recording_mic = False
            self.btn_mic.get_style_context().remove_class("btn-recording")
            self.btn_mic.set_sensitive(False)
            self.img_mic.set_from_icon_name("process-working-symbolic", Gtk.IconSize.BUTTON)
            self.btn_mic.set_tooltip_text("Transcribiendo audio con Faster-Whisper...")

            def task():
                try:
                    audio_file = self.voice_mgr.stop_recording()
                    if audio_file:
                        text = self.voice_mgr.transcribe(audio_file, language="es")
                        if text:
                            def insert_text():
                                buf = self.text_input.get_buffer()
                                curr = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()
                                new_text = f"{curr} {text}".strip() if curr else text
                                buf.set_text(new_text)
                                buf.place_cursor(buf.get_end_iter())
                                self.text_input.grab_focus()
                            GLib.idle_add(insert_text)
                except Exception as ex:
                    print(f"[Whisper Transcribe Error]: {ex}")
                finally:
                    def restore_mic():
                        self.btn_mic.set_sensitive(True)
                        self.img_mic.set_from_icon_name("audio-input-microphone-symbolic", Gtk.IconSize.BUTTON)
                        self.btn_mic.set_tooltip_text("Dictar por voz con Whisper (Español)")
                    GLib.idle_add(restore_mic)

            threading.Thread(target=task, daemon=True).start()

    def _speak_bubble_text(self, bubble, btn, img):
        if self.voice_mgr.is_playing():
            self.voice_mgr.stop_playback()
            if hasattr(self, "_active_speaking_img") and self._active_speaking_img:
                self._active_speaking_img.set_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.MENU)
            if hasattr(self, "_active_speaking_btn") and self._active_speaking_btn:
                self._active_speaking_btn.get_style_context().remove_class("btn-speaking")
            self._active_speaking_img = None
            self._active_speaking_btn = None
            return

        if not self.voice_mgr.is_installed():
            self._show_voice_settings_dialog()
            return

        raw_text = getattr(bubble, "_raw_text", "") or self.current_assistant_text
        if not raw_text or not raw_text.strip():
            return

        btn.set_sensitive(False)
        img.set_from_icon_name("process-working-symbolic", Gtk.IconSize.MENU)

        def on_finish():
            img.set_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.MENU)
            btn.get_style_context().remove_class("btn-speaking")
            btn.set_sensitive(True)
            self._active_speaking_img = None
            self._active_speaking_btn = None

        def on_play():
            btn.set_sensitive(True)
            btn.get_style_context().add_class("btn-speaking")
            img.set_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.MENU)
            self._active_speaking_img = img
            self._active_speaking_btn = btn

        try:
            cfg = self.voice_mgr.get_config()
            self.voice_mgr.play_speech_stream(
                raw_text,
                voice=cfg.get("voice", "ef_dora"),
                speed=cfg.get("speed", 1.0),
                on_start=on_play,
                on_finish=on_finish
            )
        except Exception as ex:
            on_finish()
            print(f"[Kokoro Stream Error]: {ex}")
