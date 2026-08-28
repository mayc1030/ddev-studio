# -*- coding: utf-8 -*-
"""
Diálogo de progreso con barra de estado, spinner animado, consola de logs monospace y acciones finales.
"""

import os
import subprocess
import webbrowser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class ProgressDialog(Gtk.Dialog):
    def __init__(self, parent, title="Ejecutando tarea"):
        super().__init__(title=title, transient_for=parent, flags=Gtk.DialogFlags.MODAL)
        self.set_default_size(680, 480)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.spinner = Gtk.Spinner()
        self.spinner.start()
        header_box.pack_start(self.spinner, False, False, 0)
        
        self.status_label = Gtk.Label(label="Preparando...")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_markup("<b>Iniciando operación...</b>")
        header_box.pack_start(self.status_label, True, True, 0)
        box.pack_start(header_box, False, False, 0)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_pulse_step(0.1)
        box.pack_start(self.progress_bar, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.get_style_context().add_class("console-view")
        self.text_buffer = self.text_view.get_buffer()
        scrolled.add(self.text_view)
        box.pack_start(scrolled, True, True, 0)
        
        self.action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.action_box.set_halign(Gtk.Align.END)
        box.pack_start(self.action_box, False, False, 0)
        
        self.btn_open_browser = Gtk.Button(label="🌐 Abrir en Navegador")
        self.btn_open_browser.connect("clicked", self.on_open_browser)
        self.action_box.pack_start(self.btn_open_browser, False, False, 0)
        
        self.btn_open_folder = Gtk.Button(label="📁 Abrir Carpeta")
        self.btn_open_folder.connect("clicked", self.on_open_folder)
        self.action_box.pack_start(self.btn_open_folder, False, False, 0)
        
        self.btn_close = Gtk.Button(label="Cerrar")
        self.btn_close.connect("clicked", lambda b: self.destroy())
        self.action_box.pack_start(self.btn_close, False, False, 0)
        
        self.action_box.set_no_show_all(True)
        self.action_box.hide()
        
        self.project_url = ""
        self.project_path = ""
        
        self.show_all()
        
    def append_log(self, text):
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, text)
        mark = self.text_buffer.create_mark(None, self.text_buffer.get_end_iter(), False)
        self.text_view.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
        
    def set_status(self, text, pulse=True):
        self.status_label.set_markup(f"<b>{text}</b>")
        if pulse:
            self.progress_bar.pulse()
            
    def finish(self, success, message, url="", path=""):
        self.spinner.stop()
        self.spinner.hide()
        self.progress_bar.set_fraction(1.0 if success else 0.0)
        self.project_url = url
        self.project_path = path
        
        if success:
            self.status_label.set_markup(f"<span color='#10b981'><b>✓ {message}</b></span>")
            if not url:
                self.btn_open_browser.hide()
            else:
                self.btn_open_browser.show()
            if not path:
                self.btn_open_folder.hide()
            else:
                self.btn_open_folder.show()
        else:
            self.status_label.set_markup(f"<span color='#ef4444'><b>✗ {message}</b></span>")
            self.btn_open_browser.hide()
            self.btn_open_folder.hide()
            
        self.action_box.show()
        self.btn_close.grab_focus()
        
    def on_open_browser(self, widget):
        if self.project_url:
            webbrowser.open(self.project_url)
            
    def on_open_folder(self, widget):
        if self.project_path and os.path.exists(self.project_path):
            subprocess.Popen(["xdg-open", self.project_path])
