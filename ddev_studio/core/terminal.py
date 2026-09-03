# -*- coding: utf-8 -*-
"""
Detección e invocación de emuladores de terminal de escritorio en Linux.
"""

import os
import shlex
import shutil
import subprocess
from typing import List, Optional, Tuple

from ddev_studio.logger import logger


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


def find_terminal_command() -> Optional[str]:
    """
    Retorna el primer emulador de terminal disponible en el PATH del sistema, o None si no hay ninguno.
    """
    for term in SUPPORTED_TERMINALS:
        if shutil.which(term):
            return term
    return None


def build_terminal_args(term: str, path: str, command: str = "") -> Tuple[List[str], Optional[str]]:
    """
    Construye de forma segura la lista de argumentos para el emulador de terminal y el directorio de trabajo.
    Retorna una tupla (args_list, working_dir).
    """
    clean_path = os.path.abspath(os.path.expanduser(path)) if path else os.getcwd()

    if command:
        script = f"{command}; exec bash"
        bash_cmd = f"bash -c {shlex.quote(script)}"
    else:
        bash_cmd = ""

    term_name = os.path.basename(term)

    if term_name in ["mate-terminal", "gnome-terminal", "xfce4-terminal"]:
        args = [term, f"--working-directory={clean_path}"]
        if bash_cmd:
            args.extend(["-e", bash_cmd])
        return args, clean_path

    elif term_name == "konsole":
        args = [term, "--workdir", clean_path]
        if bash_cmd:
            args.extend(["-e", "bash", "-c", f"{command}; exec bash"])
        return args, clean_path

    elif term_name == "alacritty":
        args = [term, "--working-directory", clean_path]
        if bash_cmd:
            args.extend(["-e", "bash", "-c", f"{command}; exec bash"])
        return args, clean_path

    elif term_name == "kitty":
        args = [term, "--directory", clean_path]
        if bash_cmd:
            args.extend(["bash", "-c", f"{command}; exec bash"])
        return args, clean_path

    else:
        # Fallback genérico para xterm, terminator, x-terminal-emulator
        args = [term]
        if bash_cmd:
            args.extend(["-e", bash_cmd])
        return args, clean_path


def open_terminal(path: str, command: str = "") -> Optional[subprocess.Popen]:
    """
    Abre una terminal del sistema en la ruta especificada.
    Si se proporciona un comando, se ejecuta interactivamente manteniendo abierta la sesión bash.
    Retorna la instancia de Popen creada, o None si no se encontró terminal o la ruta es inválida.
    """
    term = find_terminal_command()
    if not term:
        return None

    clean_path = os.path.abspath(os.path.expanduser(path)) if path else os.getcwd()
    if not os.path.exists(clean_path):
        try:
            os.makedirs(clean_path, exist_ok=True)
        except OSError:
            clean_path = os.getcwd()

    args, cwd = build_terminal_args(term, clean_path, command)
    try:
        return subprocess.Popen(args, cwd=cwd)
    except Exception as ex:
        logger.error(f"Error abriendo terminal {term} en {clean_path}: {ex}")
        return None



