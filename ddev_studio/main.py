# -*- coding: utf-8 -*-
"""
Punto de entrada principal para DDEV Studio.
"""

import sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk

from ddev_studio.ui.window import DDEVManagerWindow


def main():
    app = DDEVManagerWindow()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    
    # Ensure proper initial framework visibility
    first_child = app.flowbox_fw.get_child_at_index(0)
    if first_child:
        app.on_framework_selected(app.flowbox_fw, first_child)
    if hasattr(app, "combo_import_type"):
        app.on_import_type_changed(app.combo_import_type)
        
    Gtk.main()


if __name__ == "__main__":
    main()
