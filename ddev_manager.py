#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DDEV Studio - Gestor visual avanzado para entornos de desarrollo con DDEV.
Launcher de compatibilidad que delega la ejecución al paquete modular ddev_studio.
"""

import sys
import os

# Asegurar que el directorio raíz del proyecto esté en el PYTHONPATH
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from ddev_studio.main import main

if __name__ == "__main__":
    main()
