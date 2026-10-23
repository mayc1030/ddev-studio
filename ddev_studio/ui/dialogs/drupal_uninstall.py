# -*- coding: utf-8 -*-
"""
Diálogo modal de confirmación y selección de método para desinstalación de módulos en Drupal
(Directa por Drush CLI vs Interfaz Web de Drupal).
"""

import webbrowser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ddev_studio.core.drupal_tools import (
    get_drupal_uninstall_anchor,
    get_drupal_uninstall_url,
)


class DrupalUninstallDialog(Gtk.Dialog):
    RESPONSE_DRUSH = 1001
    RESPONSE_WEB = 1002

    def __init__(self, parent_window, mod_info: dict, target_site_url: str):
        mod_label = mod_info.get("label", mod_info.get("machine_name", "Módulo"))
        super().__init__(
            title=f"Desinstalar Módulo: {mod_label}",
            transient_for=parent_window,
            modal=True,
        )
        self.set_default_size(580, 440)
        self.set_resizable(False)

        self.mod_info = mod_info
        self.target_site_url = target_site_url or ""
        self.machine_name = mod_info.get("machine_name", "")
        self.mod_label = mod_label
        self.uninstall_url = get_drupal_uninstall_url(self.target_site_url, self.machine_name)

        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(16)
        box.set_margin_bottom(12)

        # 1. Cabecera Informativa
        header_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        header_card.get_style_context().add_class("option-highlight-box")

        row_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        img_warning = Gtk.Image.new_from_icon_name("dialog-warning-symbolic", Gtk.IconSize.DIALOG)
        row_top.pack_start(img_warning, False, False, 0)

        v_titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<b><big>Desinstalar módulo: {GLib.markup_escape_text(self.mod_label)}</big></b>")
        lbl_title.set_halign(Gtk.Align.START)
        v_titles.pack_start(lbl_title, False, False, 0)

        lbl_machine = Gtk.Label()
        lbl_machine.set_markup(
            f"<small><span color='#94a3b8'>Machine name:</span> <tt>{GLib.markup_escape_text(self.machine_name)}</tt></small>"
        )
        lbl_machine.set_halign(Gtk.Align.START)
        v_titles.pack_start(lbl_machine, False, False, 0)

        row_top.pack_start(v_titles, True, True, 0)

        badge_active = Gtk.Label(label="ACTIVO")
        badge_active.get_style_context().add_class("badge")
        badge_active.get_style_context().add_class("badge-running")
        badge_active.set_valign(Gtk.Align.START)
        row_top.pack_start(badge_active, False, False, 0)

        header_card.pack_start(row_top, False, False, 0)

        lbl_warn = Gtk.Label()
        lbl_warn.set_markup(
            "<span color='#e2e8f0'>Desinstalar un módulo en Drupal elimina su configuración y esquemas de base de datos. "
            "Selecciona cómo deseas proceder:</span>"
        )
        lbl_warn.set_line_wrap(True)
        lbl_warn.set_halign(Gtk.Align.START)
        header_card.pack_start(lbl_warn, False, False, 0)

        box.pack_start(header_card, False, False, 0)

        # 2. Opciones de Desinstalación
        # Opción 1: Drush CLI
        card_drush = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_drush.get_style_context().add_class("module-item-box")

        row_d_title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_d_title.pack_start(Gtk.Image.new_from_icon_name("system-run-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_d_t = Gtk.Label()
        lbl_d_t.set_markup("<b>Opción 1: Desinstalar con Drush (CLI Directo)</b>")
        lbl_d_t.set_halign(Gtk.Align.START)
        row_d_title.pack_start(lbl_d_t, True, True, 0)

        btn_action_drush = Gtk.Button()
        btn_action_drush.get_style_context().add_class("btn-quick")
        btn_action_drush.get_style_context().add_class("btn-quick-uninstall")
        b_box_drush = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_box_drush.pack_start(Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_box_drush.pack_start(Gtk.Label(label="Desinstalar con Drush"), False, False, 0)
        btn_action_drush.add(b_box_drush)
        btn_action_drush.connect("clicked", lambda b: self.response(self.RESPONSE_DRUSH))
        row_d_title.pack_start(btn_action_drush, False, False, 0)
        card_drush.pack_start(row_d_title, False, False, 0)

        lbl_d_desc = Gtk.Label()
        lbl_d_desc.set_markup(
            f"<small>Ejecuta <tt>ddev drush pm:uninstall {GLib.markup_escape_text(self.machine_name)} -y &amp;&amp; ddev drush cr</tt> en segundo plano sin salir de DDEV Studio.\n"
            f"<span color='#f59e0b'><b>Control de dependencias:</b> Si otros módulos activos dependen de este o contiene entidades con datos, Drush abortará la operación de forma segura reportando las dependencias.</span></small>"
        )
        lbl_d_desc.set_line_wrap(True)
        lbl_d_desc.set_halign(Gtk.Align.START)
        card_drush.pack_start(lbl_d_desc, False, False, 0)

        box.pack_start(card_drush, False, False, 0)

        # Opción 2: Drupal Web
        card_web = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_web.get_style_context().add_class("module-item-box")

        row_w_title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_w_title.pack_start(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_w_t = Gtk.Label()
        lbl_w_t.set_markup("<b>Opción 2: Abrir en la Interfaz Web de Drupal</b>")
        lbl_w_t.set_halign(Gtk.Align.START)
        row_w_title.pack_start(lbl_w_t, True, True, 0)

        btn_action_web = Gtk.Button()
        btn_action_web.get_style_context().add_class("btn-quick")
        b_box_web = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        b_box_web.pack_start(Gtk.Image.new_from_icon_name("folder-remote-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        b_box_web.pack_start(Gtk.Label(label="Abrir en Drupal Web"), False, False, 0)
        btn_action_web.add(b_box_web)
        btn_action_web.connect("clicked", self._on_open_web_clicked)
        row_w_title.pack_start(btn_action_web, False, False, 0)
        card_web.pack_start(row_w_title, False, False, 0)

        anchor = get_drupal_uninstall_anchor(self.machine_name)
        lbl_w_desc = Gtk.Label()
        lbl_w_desc.set_markup(
            f"<small>Abre la página oficial de desinstalación de Drupal (<tt>/admin/modules/uninstall#{GLib.markup_escape_text(anchor)}</tt>).\n"
            f"<span color='#38bdf8'><b>Recomendado si hay datos:</b> Drupal te mostrará exactamente qué campos, tipos de contenido o entidades debes purgar antes de poder desinstalar.</span></small>"
        )
        lbl_w_desc.set_line_wrap(True)
        lbl_w_desc.set_halign(Gtk.Align.START)
        card_web.pack_start(lbl_w_desc, False, False, 0)

        box.pack_start(card_web, False, False, 0)

        # 3. Botones inferiores
        self.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        self.show_all()

    def _on_open_web_clicked(self, button):
        if self.uninstall_url:
            webbrowser.open(self.uninstall_url)
        self.response(self.RESPONSE_WEB)
