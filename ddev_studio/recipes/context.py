# -*- coding: utf-8 -*-
"""
Contexto de ejecución para recetas de creación e importación en DDEV Studio.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

from ddev_studio.core.process import run_subproc


@dataclass
class RecipeContext:
    """
    Encapsula todos los parámetros y utilidades necesarias durante la ejecución de una receta.
    """
    parent_window: Any
    raw_name: str
    slug: str
    target_dir: str
    fw: Dict[str, Any]
    drupal_ver_info: Dict[str, Any]
    php_version: str
    db_type: str
    node_version: str
    auto_install: bool
    is_multisite_enabled: bool
    dialog: Any
    primary_url: str
    on_success_callback: Optional[Callable] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def log(self, text: str) -> None:
        """Agrega texto al diálogo de progreso de forma segura en el hilo de GTK."""
        if self.dialog:
            GLib.idle_add(self.dialog.append_log, text + "\n")

    def set_status(self, status: str) -> None:
        """Actualiza el texto de estado en el diálogo de progreso."""
        if self.dialog:
            GLib.idle_add(self.dialog.set_status, status)

    def run_cmd(self, cmd: list, cwd: Optional[str] = None) -> int:
        """Ejecuta un subproceso con streaming de salida al diálogo."""
        work_dir = cwd or self.target_dir
        return run_subproc(cmd, work_dir, self.dialog)
