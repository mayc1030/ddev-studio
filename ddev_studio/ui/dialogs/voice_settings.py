# -*- coding: utf-8 -*-
"""
Diálogo de configuración, diagnóstico e instalación gráfica para módulos de voz
(Whisper STT y Kokoro TTS) en DDEV Studio.
"""

import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ddev_studio.core.voice import (
    VoiceManager,
    AVAILABLE_VOICES,
    AVAILABLE_WHISPER_MODELS,
    DEFAULT_VOICE_DIR,
)
from ddev_studio.core.terminal import open_terminal
from ddev_studio.ui.dialogs.progress import ProgressDialog


class VoiceSettingsDialog(Gtk.Dialog):
    """Diálogo modal para instalar y configurar Whisper y Kokoro en DDEV Studio."""

    def __init__(self, parent_window, on_changed_callback=None):
        super().__init__(
            title="Configuración de Voz (Whisper & Kokoro)",
            transient_for=parent_window,
            modal=True
        )
        self.parent_window = parent_window
        self.on_changed_callback = on_changed_callback
        self.voice_mgr = VoiceManager()
        self.set_default_size(660, 560)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(14)
        box.set_margin_bottom(14)

        # 1. Cabecera visual
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        img_voice = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.DIALOG)
        header.pack_start(img_voice, False, False, 0)

        v_head = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<b><big>Voz y Audio con IA (Whisper & Kokoro)</big></b>")
        lbl_title.set_halign(Gtk.Align.START)
        v_head.pack_start(lbl_title, False, False, 0)

        self.lbl_subtitle = Gtk.Label()
        self.lbl_subtitle.set_markup(
            "<small>Dicta tus preguntas por micrófono (Whisper STT) y escucha las respuestas "
            "en voz alta con naturalidad en español (Kokoro-82M TTS).</small>"
        )
        self.lbl_subtitle.set_halign(Gtk.Align.START)
        self.lbl_subtitle.set_line_wrap(True)
        v_head.pack_start(self.lbl_subtitle, False, False, 0)
        header.pack_start(v_head, True, True, 0)
        box.pack_start(header, False, False, 0)

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(sep1, False, False, 0)

        # 2. Tarjeta de Diagnóstico y Estado
        self.status_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.status_card.get_style_context().add_class("kpi-card")

        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_st_title = Gtk.Label()
        lbl_st_title.set_markup("<b>Estado del Motor de Voz:</b>")
        status_row.pack_start(lbl_st_title, False, False, 0)

        self.badge_status = Gtk.Label(label="Comprobando...")
        self.badge_status.get_style_context().add_class("badge")
        status_row.pack_start(self.badge_status, False, False, 0)
        self.status_card.pack_start(status_row, False, False, 0)

        self.lbl_status_details = Gtk.Label()
        self.lbl_status_details.set_halign(Gtk.Align.START)
        self.lbl_status_details.set_line_wrap(True)
        self.status_card.pack_start(self.lbl_status_details, False, False, 0)

        # Botones de Acción de Instalación
        self.install_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.install_actions_box.set_margin_top(4)

        self.btn_install = Gtk.Button()
        b_in = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_in.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        self.lbl_btn_install = Gtk.Label(label="Instalar Módulos de Voz")
        b_in.pack_start(self.lbl_btn_install, False, False, 0)
        self.btn_install.add(b_in)
        self.btn_install.get_style_context().add_class("btn-primary")
        self.btn_install.connect("clicked", lambda b: self._on_install_clicked())
        self.install_actions_box.pack_start(self.btn_install, False, False, 0)

        self.btn_install_term = Gtk.Button()
        b_it = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_it.pack_start(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_it.pack_start(Gtk.Label(label="Instalar Dependencias en Terminal"), False, False, 0)
        self.btn_install_term.add(b_it)
        self.btn_install_term.get_style_context().add_class("btn-quick")
        self.btn_install_term.connect("clicked", lambda b: self._on_install_terminal_clicked())
        self.install_actions_box.pack_start(self.btn_install_term, False, False, 0)

        self.btn_test_voice = Gtk.Button()
        b_tv = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.img_test_voice = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.BUTTON)
        b_tv.pack_start(self.img_test_voice, False, False, 0)
        self.lbl_test_voice = Gtk.Label(label="Probar Voz en Español")
        b_tv.pack_start(self.lbl_test_voice, False, False, 0)
        self.btn_test_voice.add(b_tv)
        self.btn_test_voice.get_style_context().add_class("btn-quick")
        self.btn_test_voice.connect("clicked", lambda b: self._on_test_voice_clicked())
        self.install_actions_box.pack_start(self.btn_test_voice, False, False, 0)

        self.status_card.pack_start(self.install_actions_box, False, False, 0)
        box.pack_start(self.status_card, False, False, 0)

        # 3. Preferencias de Voz (Voces, Velocidad, Auto-lectura)
        pref_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        lbl_pref_title = Gtk.Label()
        lbl_pref_title.set_markup("<b>Preferencias de Voz y Audio:</b>")
        lbl_pref_title.set_halign(Gtk.Align.START)
        pref_frame.pack_start(lbl_pref_title, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        # Selector de Voz Kokoro
        lbl_voice = Gtk.Label(label="Voz en Español:")
        lbl_voice.set_halign(Gtk.Align.START)
        grid.attach(lbl_voice, 0, 0, 1, 1)

        self.combo_voice = Gtk.ComboBoxText()
        for v in AVAILABLE_VOICES:
            self.combo_voice.append(v["id"], v["name"])
        grid.attach(self.combo_voice, 1, 0, 1, 1)

        # Selector de Velocidad
        lbl_speed = Gtk.Label(label="Velocidad:")
        lbl_speed.set_halign(Gtk.Align.START)
        grid.attach(lbl_speed, 0, 1, 1, 1)

        self.combo_speed = Gtk.ComboBoxText()
        self.combo_speed.append("0.8", "0.8x (Lento y claro)")
        self.combo_speed.append("1.0", "1.0x (Normal - Recomendado)")
        self.combo_speed.append("1.2", "1.2x (Ágil)")
        self.combo_speed.append("1.4", "1.4x (Rápido)")
        grid.attach(self.combo_speed, 1, 1, 1, 1)

        # Selector de Modelo Whisper
        lbl_whisper = Gtk.Label(label="Modelo Whisper (STT):")
        lbl_whisper.set_halign(Gtk.Align.START)
        grid.attach(lbl_whisper, 0, 2, 1, 1)

        self.combo_whisper = Gtk.ComboBoxText()
        for wm in AVAILABLE_WHISPER_MODELS:
            self.combo_whisper.append(wm["id"], wm["name"])
        grid.attach(self.combo_whisper, 1, 2, 1, 1)

        pref_frame.pack_start(grid, False, False, 0)

        # Checkbox Auto-lectura
        self.chk_auto_speak = Gtk.CheckButton(label="Leer automáticamente en voz alta cada respuesta que genere la IA")
        self.chk_auto_speak.set_tooltip_text(
            "Al marcar esta opción, tan pronto como el Asistente termine de responder, "
            "Kokoro sintetizará la respuesta en español a través de tus altavoces."
        )
        pref_frame.pack_start(self.chk_auto_speak, False, False, 0)

        box.pack_start(pref_frame, False, False, 0)

        # Conectar señales de cambio para auto-guardado
        self.combo_voice.connect("changed", self._on_pref_changed)
        self.combo_speed.connect("changed", self._on_pref_changed)
        self.combo_whisper.connect("changed", self._on_pref_changed)
        self.chk_auto_speak.connect("toggled", self._on_pref_changed)

        # Botón Cerrar
        btn_close = Gtk.Button(label="Cerrar")
        btn_close.connect("clicked", lambda b: self.destroy())
        self.get_action_area().pack_end(btn_close, False, False, 0)

        self.load_preferences()
        self.refresh_status()
        self.show_all()

    # -------------------------------------------------------------------------
    # Carga y Actualización de Estado
    # -------------------------------------------------------------------------
    def load_preferences(self):
        """Carga las preferencias persistentes en los controles gráficos."""
        cfg = self.voice_mgr.get_config()
        self.combo_voice.set_active_id(cfg.get("voice", "ef_dora"))
        self.combo_speed.set_active_id(str(cfg.get("speed", 1.0)))
        self.combo_whisper.set_active_id(cfg.get("whisper_model", "base"))
        self.chk_auto_speak.set_active(bool(cfg.get("auto_speak", False)))

    def _on_pref_changed(self, widget):
        """Persiste los cambios inmediatamente."""
        sel_voice = self.combo_voice.get_active_id() or "ef_dora"
        try:
            sel_speed = float(self.combo_speed.get_active_id() or 1.0)
        except Exception:
            sel_speed = 1.0
        sel_whisper = self.combo_whisper.get_active_id() or "base"
        auto_speak = self.chk_auto_speak.get_active()

        self.voice_mgr.update_config(
            voice=sel_voice,
            speed=sel_speed,
            whisper_model=sel_whisper,
            auto_speak=auto_speak
        )
        if self.on_changed_callback:
            self.on_changed_callback()

    def refresh_status(self):
        """Consulta el estado del entorno de voz en un hilo secundario."""
        def check_task():
            deps = self.voice_mgr.check_system_dependencies()
            missing_pkgs = self.voice_mgr.get_missing_system_packages()
            is_ready = self.voice_mgr.is_installed()

            def update_ui():
                self.badge_status.get_style_context().remove_class("badge-running")
                self.badge_status.get_style_context().remove_class("badge-paused")

                if is_ready:
                    self.badge_status.set_text("✔ Instalado y Listo")
                    self.badge_status.get_style_context().add_class("badge-running")
                    self.lbl_status_details.set_markup(
                        "<span>• <b>Whisper STT:</b> Faster-Whisper activo en CPU.<br/>"
                        "• <b>Kokoro-82M TTS:</b> Voces y modelo ONNX listos.<br/>"
                        f"• <b>Directorio:</b> <tt>{DEFAULT_VOICE_DIR}</tt></span>"
                    )
                    self.lbl_btn_install.set_text("Reinstalar / Reparar Voz")
                    self.btn_install_term.set_visible(False)
                    self.btn_test_voice.set_visible(True)
                else:
                    self.badge_status.set_text("⚠ No Instalado")
                    self.badge_status.get_style_context().add_class("badge-paused")
                    if missing_pkgs:
                        pkgs_txt = ", ".join(missing_pkgs)
                        self.lbl_status_details.set_markup(
                            f"<span>Faltan componentes en el sistema: <b>{pkgs_txt}</b>.<br/>"
                            "Haz clic en <b>Instalar Módulos de Voz</b> para configurar todo automáticamente.</span>"
                        )
                        self.btn_install_term.set_visible(True)
                    else:
                        self.lbl_status_details.set_markup(
                            "<span>El entorno virtual y los modelos de voz aún no han sido descargados.<br/>"
                            "Haz clic en <b>Instalar Módulos de Voz</b> para iniciar la descarga.</span>"
                        )
                        self.btn_install_term.set_visible(False)

                    self.lbl_btn_install.set_text("Instalar Módulos de Voz (1 Clic)")
                    self.btn_test_voice.set_visible(False)

            GLib.idle_add(update_ui)

        threading.Thread(target=check_task, daemon=True).start()

    # -------------------------------------------------------------------------
    # Acciones de Instalación y Pruebas
    # -------------------------------------------------------------------------
    def _on_install_clicked(self):
        """Inicia el proceso guiado de instalación desatendida con ProgressDialog."""
        dialog = ProgressDialog(self.parent_window, title="Instalación de Módulos de Voz (Whisper + Kokoro)")
        dialog.set_status("Iniciando preparación del entorno de voz...")

        def task():
            def log(t):
                GLib.idle_add(dialog.append_log, t)

            def set_p(pct):
                GLib.idle_add(dialog.progress_bar.set_fraction, pct)

            try:
                log("⚡ Comprobando dependencias del sistema operativo...\n")
                missing = self.voice_mgr.get_missing_system_packages()
                if missing:
                    log(f"ℹ Se detectaron paquetes de sistema pendientes: {', '.join(missing)}\n")
                    log("ℹ Solicitando autorización administrativa (PolicyKit) para apt-get...\n\n")

                    cmd = self.voice_mgr.get_system_install_command(use_pkexec=True)
                    import subprocess
                    p_sys = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in iter(p_sys.stdout.readline, ''):
                        log(f"  {line}")
                    p_sys.stdout.close()
                    p_sys.wait()

                    if p_sys.returncode != 0:
                        log("\n❌ La instalación de paquetes del sistema no pudo completarse.\n")
                        log("💡 Puedes pulsar 'Instalar Dependencias en Terminal' para ingresar sudo manualmente.\n")
                        GLib.idle_add(dialog.finish, False, "Fallo al instalar paquetes de sistema con apt.")
                        GLib.idle_add(self.refresh_status)
                        return

                    log("✔ Dependencias de sistema instaladas con éxito.\n\n")

                # Proceder con la instalación de Python y modelos
                ok, msg = self.voice_mgr.install(on_log=log, on_progress=set_p)
                GLib.idle_add(dialog.finish, ok, msg)
                GLib.idle_add(self.refresh_status)
                if self.on_changed_callback:
                    GLib.idle_add(self.on_changed_callback)

            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {ex}")
                GLib.idle_add(self.refresh_status)

        threading.Thread(target=task, daemon=True).start()

    def _on_install_terminal_clicked(self):
        """Abre la terminal del sistema para ejecutar sudo apt-get install de las dependencias."""
        missing = self.voice_mgr.get_missing_system_packages()
        if not missing:
            missing = ["python3-venv", "python3-pip", "espeak-ng", "ffmpeg"]
        cmd_str = f"sudo apt-get update && sudo apt-get install -y {' '.join(missing)}"
        open_terminal(None, cmd_str)
        GLib.timeout_add(5000, self.refresh_status)

    def _on_test_voice_clicked(self):
        """Sintetiza una frase de prueba en español con Kokoro y la reproduce."""
        if self.voice_mgr.is_playing():
            self.voice_mgr.stop_playback()
            self.lbl_test_voice.set_text("Probar Voz en Español")
            self.img_test_voice.set_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.BUTTON)
            return

        self.lbl_test_voice.set_text("Generando audio...")
        self.btn_test_voice.set_sensitive(False)

        def run_test():
            try:
                cfg = self.voice_mgr.get_config()
                sample_text = (
                    "Hola, soy tu asistente de desarrollo en DDEV Studio. "
                    "El motor de voz Kokoro y Whisper están configurados y funcionando perfectamente."
                )
                wav_path = self.voice_mgr.synthesize(
                    sample_text,
                    voice=cfg.get("voice", "ef_dora"),
                    speed=cfg.get("speed", 1.0)
                )

                def on_finish():
                    self.lbl_test_voice.set_text("Probar Voz en Español")
                    self.img_test_voice.set_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.BUTTON)
                    self.btn_test_voice.set_sensitive(True)

                def on_play():
                    self.lbl_test_voice.set_text("Reproduciendo... (Clic para detener)")
                    self.img_test_voice.set_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.BUTTON)
                    self.btn_test_voice.set_sensitive(True)
                    self.voice_mgr.play_audio(wav_path, on_finish=on_finish)

                GLib.idle_add(on_play)

            except Exception as ex:
                def on_err():
                    self.lbl_test_voice.set_text("Error al sintetizar")
                    self.btn_test_voice.set_sensitive(True)
                    self.img_test_voice.set_from_icon_name("dialog-error-symbolic", Gtk.IconSize.BUTTON)
                    print(f"[Voice Test Error]: {ex}")
                GLib.idle_add(on_err)

        threading.Thread(target=run_test, daemon=True).start()
