# -*- coding: utf-8 -*-
"""
Detección e invocación de emuladores de terminal de escritorio en Linux.
"""

import shutil
import subprocess

SUPPORTED_TERMINALS = [
    "mate-terminal",
    "gnome-terminal",
    "xfce4-terminal",
    "konsole",
    "terminator",
    "alacritty",
    "kitty",
    "x-terminal-emulator",
    "xterm"
]


def find_terminal_command():
    """
    Retorna el primer emulador de terminal disponible en el PATH del sistema, o None si no hay ninguno.
    """
    for term in SUPPORTED_TERMINALS:
        if shutil.which(term):
            return term
    return None


def open_terminal(path, command=""):
    """
    Abre una terminal del sistema en la ruta especificada.
    Si se proporciona un comando, se ejecuta interactivamente manteniendo abierta la sesión bash.
    """
    term = find_terminal_command()
    if not term:
        return

    if term in ["mate-terminal", "gnome-terminal", "xfce4-terminal"]:
        if command:
            subprocess.Popen([term, f"--working-directory={path}", "-e", f"bash -c '{command}; exec bash'"])
        else:
            subprocess.Popen([term, f"--working-directory={path}"])
    else:
        if command:
            subprocess.Popen([term, "-e", f"bash -c '{command}; exec bash'"], cwd=path)
        else:
            subprocess.Popen([term], cwd=path)
