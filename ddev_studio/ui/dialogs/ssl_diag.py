# -*- coding: utf-8 -*-
"""
Diálogo de diagnóstico, instalación y reparación de certificados SSL locales (mkcert y libnss3-tools).
Permite asegurar que Chrome, Chromium y Firefox confíen en los dominios .ddev.site.
"""

import threading
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from ddev_studio.core.ssl_tools import (
    check_ssl_health,
    run_mkcert_install,
    get_certutil_install_command,
    is_certutil_installed,
    is_mkcert_installed
)


class SSLDiagDialog(Gtk.Dialog):
    """Diálogo modal para diagnóstico y reparación de certificados HTTPS locales."""

    def __init__(self, parent_window):
        super().__init__(
            title="Diagnóstico y Certificados SSL (HTTPS)",
            transient_for=parent_window,
            modal=True
        )
        self.set_default_size(620, 520)

        box = self.get_content_area()
        box.set_spacing(14)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(14)
        box.set_margin_bottom(14)

        # 1. Cabecera visual
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.img_status = Gtk.Image.new_from_icon_name("channel-secure-symbolic", Gtk.IconSize.DIALOG)
        header.pack_start(self.img_status, False, False, 0)

        v_head = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<b><big>Certificados SSL Locales (mkcert)</big></b>")
        lbl_title.set_halign(Gtk.Align.START)
        v_head.pack_start(lbl_title, False, False, 0)

        self.lbl_subtitle = Gtk.Label()
        self.lbl_subtitle.set_halign(Gtk.Align.START)
        self.lbl_subtitle.set_line_wrap(True)
        v_head.pack_start(self.lbl_subtitle, False, False, 0)

        header.pack_start(v_head, True, True, 0)
        box.pack_start(header, False, False, 0)

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(sep1, False, False, 0)

        # 2. Checklist de Diagnóstico del Sistema
        chk_frame = Gtk.Frame(label=" Verificación de Componentes del Sistema ")
        chk_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        chk_box.set_margin_start(12)
        chk_box.set_margin_end(12)
        chk_box.set_margin_top(10)
        chk_box.set_margin_bottom(10)

        self.lbl_chk_mkcert = Gtk.Label()
        self.lbl_chk_mkcert.set_halign(Gtk.Align.START)
        chk_box.pack_start(self.lbl_chk_mkcert, False, False, 0)

        self.lbl_chk_certutil = Gtk.Label()
        self.lbl_chk_certutil.set_halign(Gtk.Align.START)
        chk_box.pack_start(self.lbl_chk_certutil, False, False, 0)

        self.lbl_chk_trust = Gtk.Label()
        self.lbl_chk_trust.set_halign(Gtk.Align.START)
        self.lbl_chk_trust.set_line_wrap(True)
        chk_box.pack_start(self.lbl_chk_trust, False, False, 0)

        chk_frame.add(chk_box)
        box.pack_start(chk_frame, False, False, 0)

        # 3. Acciones recomendadas según el estado
        self.act_frame = Gtk.Frame(label=" Acciones y Solución ")
        self.act_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.act_box.set_margin_start(12)
        self.act_box.set_margin_end(12)
        self.act_box.set_margin_top(10)
        self.act_box.set_margin_bottom(10)
        self.act_frame.add(self.act_box)
        box.pack_start(self.act_frame, False, False, 0)

        # 4. Consola de salida de operaciones
        lbl_log = Gtk.Label()
        lbl_log.set_markup("<b>Salida del proceso:</b>")
        lbl_log.set_halign(Gtk.Align.START)
        box.pack_start(lbl_log, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_buffer = self.text_view.get_buffer()
        scrolled.add(self.text_view)
        box.pack_start(scrolled, True, True, 0)

        # 5. Barra inferior con botones de cierre y actualización
        bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bbox.set_halign(Gtk.Align.END)

        btn_refresh = Gtk.Button.new_with_mnemonic("_Actualizar Estado")
        btn_refresh.connect("clicked", lambda b: self.refresh_status())
        bbox.pack_start(btn_refresh, False, False, 0)

        btn_close = Gtk.Button.new_with_mnemonic("_Cerrar")
        btn_close.connect("clicked", lambda b: self.destroy())
        bbox.pack_start(btn_close, False, False, 0)

        box.pack_start(bbox, False, False, 0)

        self.refresh_status()
        self.show_all()

    def log(self, text: str):
        """Agrega texto a la consola del diálogo."""
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, text + "\n")
        self.text_view.scroll_to_iter(self.text_buffer.get_end_iter(), 0.0, False, 0.0, 0.0)

    def refresh_status(self):
        """Actualiza el diagnóstico visual y las opciones disponibles."""
        health = check_ssl_health()

        # Limpiar acciones anteriores
        for child in self.act_box.get_children():
            self.act_box.remove(child)

        # 1. Checklist
        if health["mkcert_installed"]:
            self.lbl_chk_mkcert.set_markup("• <b>mkcert (Generador SSL):</b> <span foreground='green'>✅ Instalado</span>")
        else:
            self.lbl_chk_mkcert.set_markup("• <b>mkcert (Generador SSL):</b> <span foreground='red'>❌ No encontrado en PATH</span>")

        if health["certutil_installed"]:
            self.lbl_chk_certutil.set_markup("• <b>certutil (libnss3-tools):</b> <span foreground='green'>✅ Instalado</span> (Chrome/Firefox soportados)")
        else:
            self.lbl_chk_certutil.set_markup("• <b>certutil (libnss3-tools):</b> <span foreground='#d97706'>⚠️ No instalado</span> (Requerido para navegadores en Linux)")

        # 2. Encabezado y acciones
        if health["healthy"]:
            self.img_status.set_from_icon_name("channel-secure-symbolic", Gtk.IconSize.DIALOG)
            self.lbl_subtitle.set_markup("<span foreground='green'><b>Tu sistema está listo y configurado para HTTPS local seguro.</b></span>\nChrome, Chromium y Firefox reconocen la entidad certificadora.")
            self.lbl_chk_trust.set_markup("• <b>Estado General:</b> <span foreground='green'>Óptimo</span>")

            lbl_ok = Gtk.Label()
            lbl_ok.set_markup("Si cambiaste de navegador o experimentas alguna advertencia en algún dominio, puedes reinstalar los certificados en los almacenes locales:")
            lbl_ok.set_halign(Gtk.Align.START)
            lbl_ok.set_line_wrap(True)
            self.act_box.pack_start(lbl_ok, False, False, 0)

            btn_run_mkcert = Gtk.Button.new_with_label("Reinstalar / Registrar Certificados (mkcert -install)")
            btn_run_mkcert.connect("clicked", self.on_run_mkcert)
            self.act_box.pack_start(btn_run_mkcert, False, False, 0)

        elif not health["mkcert_installed"]:
            self.img_status.set_from_icon_name("dialog-error-symbolic", Gtk.IconSize.DIALOG)
            self.lbl_subtitle.set_markup("<span foreground='red'><b>Falta la herramienta mkcert.</b></span>")
            self.lbl_chk_trust.set_markup("• <b>Estado General:</b> <span foreground='red'>Incompleto</span>")

            lbl_mk_help = Gtk.Label()
            lbl_mk_help.set_markup("Para instalar mkcert en Ubuntu/Debian ejecuta:\n<b>sudo apt install -y libnss3-tools && curl -JLO 'https://dl.filippo.io/mkcert/latest?for=linux/amd64' && chmod +x mkcert-v*-linux-amd64 && sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert && mkcert -install</b>")
            lbl_mk_help.set_halign(Gtk.Align.START)
            lbl_mk_help.set_line_wrap(True)
            self.act_box.pack_start(lbl_mk_help, False, False, 0)

        elif not health["certutil_installed"]:
            self.img_status.set_from_icon_name("dialog-warning-symbolic", Gtk.IconSize.DIALOG)
            self.lbl_subtitle.set_markup("<span foreground='#d97706'><b>Advertencia: Los navegadores mostrarán 'La conexión no es privada'</b></span>\nFalta la utilidad <b>certutil</b> para importar los certificados en Chrome y Firefox.")
            self.lbl_chk_trust.set_markup("• <b>Estado General:</b> <span foreground='#d97706'>Requiere acción</span>")

            lbl_info = Gtk.Label()
            lbl_info.set_markup("Para solucionar el error <code>NET::ERR_CERT_AUTHORITY_INVALID</code>, instala el paquete <b>libnss3-tools</b>:")
            lbl_info.set_halign(Gtk.Align.START)
            self.act_box.pack_start(lbl_info, False, False, 0)

            # Caja con comando y botón de copia
            cmd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            install_cmd = f"{get_certutil_install_command()} && mkcert -install"
            entry_cmd = Gtk.Entry()
            entry_cmd.set_text(install_cmd)
            entry_cmd.set_editable(False)
            entry_cmd.set_hexpand(True)
            cmd_box.pack_start(entry_cmd, True, True, 0)

            btn_copy = Gtk.Button.new_with_label("Copiar Comando")
            btn_copy.connect("clicked", lambda b, c=install_cmd: self.copy_to_clipboard(c))
            cmd_box.pack_start(btn_copy, False, False, 0)
            self.act_box.pack_start(cmd_box, False, False, 0)

            # Botón para instalación asistida
            btn_install_pkg = Gtk.Button.new_with_label("⚡ Instalar libnss3-tools y Registrar Certificados")
            btn_install_pkg.get_style_context().add_class("suggested-action")
            btn_install_pkg.connect("clicked", self.on_auto_install_certutil)
            self.act_box.pack_start(btn_install_pkg, False, False, 0)

        self.act_box.show_all()

    def copy_to_clipboard(self, text: str):
        """Copia el comando al portapapeles del sistema."""
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        self.log("📋 Comando copiado al portapapeles:")
        self.log(f"   {text}")

    def on_run_mkcert(self, widget):
        """Ejecuta mkcert -install en segundo plano."""
        self.log("🚀 Ejecutando 'mkcert -install'...")
        widget.set_sensitive(False)

        def worker():
            success, output = run_mkcert_install()
            def finish():
                self.log(output)
                if success:
                    self.log("✅ Certificados registrados exitosamente.")
                    self.log("💡 RECUERDA: Cierra y reinicia tu navegador para que cargue los certificados.")
                else:
                    self.log("❌ Ocurrió un error registrando los certificados.")
                widget.set_sensitive(True)
                self.refresh_status()
            GLib.idle_add(finish)

        threading.Thread(target=worker, daemon=True).start()

    def on_auto_install_certutil(self, widget):
        """Intenta instalar libnss3-tools usando pkexec para pedir credenciales gráficas."""
        widget.set_sensitive(False)
        self.log("⏳ Solicitando instalación de libnss3-tools...")

        def worker():
            cmd = ["pkexec", "sh", "-c", "apt-get update && apt-get install -y libnss3-tools"]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if proc.returncode == 0:
                    GLib.idle_add(self.log, "✅ 'libnss3-tools' se instaló con éxito.")
                    # Ahora ejecutar mkcert -install
                    success_mk, out_mk = run_mkcert_install()
                    GLib.idle_add(self.log, out_mk)
                    if success_mk:
                        GLib.idle_add(self.log, "✅ Certificados registrados en Chrome y Firefox.")
                        GLib.idle_add(self.log, "💡 IMPORTANTE: Reinicia tu navegador cerrando todas sus ventanas.")
                else:
                    GLib.idle_add(self.log, f"❌ No se pudo instalar el paquete:\n{proc.stderr}")
            except Exception as e:
                GLib.idle_add(self.log, f"❌ Error ejecutando instalador: {e}")

            GLib.idle_add(lambda: widget.set_sensitive(True))
            GLib.idle_add(self.refresh_status)

        threading.Thread(target=worker, daemon=True).start()
