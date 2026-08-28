# -*- coding: utf-8 -*-
"""
Diálogo para configurar y generar flujos de trabajo de Integración Continua (CI/CD) con GitHub Actions.
"""

import os
import subprocess
import webbrowser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

from ddev_studio.core.ci_templates import (
    detect_git_repo,
    detect_existing_workflows,
    generate_ci_workflow,
    save_ci_workflow
)


class CIDialog(Gtk.Dialog):
    def __init__(self, parent_window, approot, proj_name, tech_type):
        super().__init__(title=f"Integración Continua (GitHub Actions) - {proj_name}", transient_for=parent_window, modal=True)
        self.set_default_size(680, 560)
        self.approot = approot
        self.proj_name = proj_name
        self.tech_type = tech_type
        
        self.git_info = detect_git_repo(approot)
        self.existing_wf = detect_existing_workflows(approot)
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # 1. Header Banner
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.get_style_context().add_class("project-card")
        
        img_ci = Gtk.Image.new_from_icon_name("system-run-symbolic", Gtk.IconSize.DIALOG)
        header.pack_start(img_ci, False, False, 0)
        
        v_h = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<b><big>Automatización CI/CD con GitHub Actions</big></b>")
        lbl_title.set_halign(Gtk.Align.START)
        v_h.pack_start(lbl_title, False, False, 0)
        
        git_desc = f"Tecnología: <b>{tech_type.upper()}</b>"
        if self.git_info["has_git"]:
            git_desc += f" | Rama: <b>{self.git_info['branch']}</b>"
            if self.git_info["github_url"]:
                git_desc += f" | 🌐 <a href='{self.git_info['github_url']}'>Repositorio GitHub</a>"
        else:
            git_desc += " | ⚠️ <i>Sin repositorio Git local</i>"
            
        lbl_sub = Gtk.Label()
        lbl_sub.set_markup(f"<small>{git_desc}</small>")
        lbl_sub.set_halign(Gtk.Align.START)
        v_h.pack_start(lbl_sub, False, False, 0)
        header.pack_start(v_h, True, True, 0)
        box.pack_start(header, False, False, 0)
        
        # 2. Options Grid
        frame_opts = Gtk.Frame(label=" Opciones del Pipeline ")
        box_opts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box_opts.set_margin_start(12)
        box_opts.set_margin_end(12)
        box_opts.set_margin_top(8)
        box_opts.set_margin_bottom(8)
        
        self.chk_tests = Gtk.CheckButton(label="Ejecutar Pruebas Automatizadas (Unit Tests / Testing Suite)")
        self.chk_tests.set_active(True)
        self.chk_tests.connect("toggled", lambda b: self.refresh_preview())
        box_opts.pack_start(self.chk_tests, False, False, 0)
        
        self.chk_lint = Gtk.CheckButton(label="Validar Estándares de Código y Linter (PHPCS / ESLint / Flake8)")
        self.chk_lint.set_active(True)
        self.chk_lint.connect("toggled", lambda b: self.refresh_preview())
        box_opts.pack_start(self.chk_lint, False, False, 0)
        
        self.chk_sec = Gtk.CheckButton(label="Auditoría de Seguridad de Dependencias (composer audit / npm audit)")
        self.chk_sec.set_active(True)
        self.chk_sec.connect("toggled", lambda b: self.refresh_preview())
        box_opts.pack_start(self.chk_sec, False, False, 0)
        
        is_drupal = "drupal" in tech_type.lower()
        self.chk_ddev_action = Gtk.CheckButton(label="Levantar entorno DDEV en GitHub Actions (ddev/github-action)")
        self.chk_ddev_action.set_active(is_drupal)
        self.chk_ddev_action.set_visible(is_drupal)
        self.chk_ddev_action.connect("toggled", lambda b: self.refresh_preview())
        box_opts.pack_start(self.chk_ddev_action, False, False, 0)
        
        frame_opts.add(box_opts)
        box.pack_start(frame_opts, False, False, 0)
        
        # 3. YAML Preview Frame
        lbl_prev_title = Gtk.Label()
        lbl_prev_title.set_markup("<b>Vista Previa del Archivo (.github/workflows/ci.yml):</b>")
        lbl_prev_title.set_halign(Gtk.Align.START)
        box.pack_start(lbl_prev_title, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(160)
        
        self.txt_preview = Gtk.TextView()
        self.txt_preview.set_editable(True)
        self.txt_preview.set_monospace(True)
        self.txt_preview.set_wrap_mode(Gtk.WrapMode.NONE)
        scrolled.add(self.txt_preview)
        box.pack_start(scrolled, True, True, 0)
        
        # 4. Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(6)
        
        btn_cancel = Gtk.Button(label="Cerrar")
        btn_cancel.connect("clicked", lambda b: self.destroy())
        btn_box.pack_start(btn_cancel, False, False, 0)
        
        btn_generate = Gtk.Button()
        b_gen = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_gen.pack_start(Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_gen.pack_start(Gtk.Label(label="Generar e Instalar en .github/"), False, False, 0)
        btn_generate.add(b_gen)
        btn_generate.get_style_context().add_class("btn-primary")
        btn_generate.connect("clicked", self.on_generate_clicked)
        btn_box.pack_start(btn_generate, False, False, 0)
        
        box.pack_start(btn_box, False, False, 0)
        
        self.refresh_preview()
        self.show_all()
        
    def get_options(self):
        return {
            "include_tests": self.chk_tests.get_active(),
            "include_lint": self.chk_lint.get_active(),
            "include_security": self.chk_sec.get_active(),
            "use_ddev_action": self.chk_ddev_action.get_active() if self.chk_ddev_action.get_visible() else False
        }
        
    def refresh_preview(self):
        opts = self.get_options()
        yaml_content = generate_ci_workflow(self.tech_type, opts)
        buf = self.txt_preview.get_buffer()
        buf.set_text(yaml_content)
        
    def on_generate_clicked(self, btn):
        buf = self.txt_preview.get_buffer()
        content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        
        ok, res = save_ci_workflow(self.approot, content, "ci.yml")
        if ok:
            msg_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="¡Pipeline de GitHub Actions Creado con Éxito!"
            )
            msg_dialog.format_secondary_markup(
                f"El archivo se guardó en:<br/><tt><b>{res}</b></tt><br/><br/>"
                "<b>¿Cómo activarlo en GitHub?</b><br/>"
                "Ejecuta estos comandos en la terminal de tu proyecto:<br/>"
                "<tt><b>git add .github/</b></tt><br/>"
                "<tt><b>git commit -m \"ci: agregar GitHub Actions\"</b></tt><br/>"
                "<tt><b>git push</b></tt><br/><br/>"
                "<i>GitHub lo activará automáticamente en cuanto reciba el push.</i>"
            )
            msg_dialog.run()
            msg_dialog.destroy()
            self.destroy()
        else:
            err_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error al guardar el workflow"
            )
            err_dialog.format_secondary_text(f"Detalle: {res}")
            err_dialog.run()
            err_dialog.destroy()
