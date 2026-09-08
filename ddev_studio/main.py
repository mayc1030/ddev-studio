# -*- coding: utf-8 -*-
"""
Punto de entrada principal para DDEV Studio.
"""

import sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk

from ddev_studio.logger import setup_logger, logger
from ddev_studio.ui.window import DDEVManagerWindow


def main():
    setup_logger()
    logger.info("Iniciando DDEV Studio...")
    app = DDEVManagerWindow()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    app.init_state()
    Gtk.main()


if __name__ == "__main__":
    main()
