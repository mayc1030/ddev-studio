# -*- coding: utf-8 -*-
"""
Ejecución de subprocesos con streaming a consola y manejo de errores.
"""

import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib


def run_subproc(cmd, cwd, dialog):
    """
    Ejecuta un comando en el subproceso especificado enviando la salida en tiempo real
    al buffer de texto del diálogo de progreso. Lanza RuntimeError si falla.
    """
    cmd_str = " ".join(cmd)
    if dialog:
        GLib.idle_add(dialog.append_log, f"\n$ {cmd_str}\n")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    if proc.stdout:
        for line in iter(proc.stdout.readline, ''):
            if line and dialog:
                GLib.idle_add(dialog.append_log, line)
        proc.stdout.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"El comando falló con código {proc.returncode}: {cmd_str}")
    return proc.returncode
