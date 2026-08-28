# -*- coding: utf-8 -*-
"""
Funciones auxiliares para componentes de interfaz de usuario en GTK3.
"""

import os
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, GdkPixbuf

from ddev_studio.constants import ICONS_DIR


def create_icon_menu_item(icon_name, label_text, callback=None):
    """Crea un elemento de menú con icono y etiqueta."""
    item = Gtk.MenuItem()
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
    lbl = Gtk.Label(label=label_text, halign=Gtk.Align.START)
    lbl.set_hexpand(True)
    hbox.pack_start(icon, False, False, 0)
    hbox.pack_start(lbl, True, True, 0)
    item.add(hbox)
    if callback:
        item.connect("activate", callback)
    return item


def load_icon(name, size=48):
    """Carga un icono SVG/PNG desde el directorio de recursos escalado al tamaño especificado."""
    path = os.path.join(ICONS_DIR, name)
    if os.path.exists(path):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        except Exception:
            pass
    return None
