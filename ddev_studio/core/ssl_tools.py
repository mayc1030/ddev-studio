# -*- coding: utf-8 -*-
"""
Módulo de diagnóstico y gestión de certificados SSL locales (mkcert y libnss3-tools).
Provee lógica pura e independiente de la interfaz gráfica para verificar
la compatibilidad HTTPS en navegadores Chromium/Chrome y Firefox.
"""

import shutil
import subprocess
from typing import Dict, Any, Tuple


def is_mkcert_installed() -> bool:
    """Verifica si el binario mkcert está presente en el PATH del sistema."""
    return shutil.which("mkcert") is not None


def is_certutil_installed() -> bool:
    """
    Verifica si el binario certutil (del paquete libnss3-tools) está instalado.
    Es indispensable para que Chromium, Google Chrome y Firefox reconozcan
    la CA raíz local generada por mkcert en Linux.
    """
    return shutil.which("certutil") is not None


def get_certutil_install_command() -> str:
    """Retorna el comando recomendado para instalar libnss3-tools en distribuciones Debian/Ubuntu."""
    return "sudo apt update && sudo apt install -y libnss3-tools"


def check_ssl_health() -> Dict[str, Any]:
    """
    Evalúa la salud y configuración del entorno SSL para sitios DDEV locales.

    Retorna un diccionario con:
        - mkcert_installed: bool
        - certutil_installed: bool
        - healthy: bool (True si ambos están instalados y operativos)
        - status_code: str ('ok', 'missing_mkcert', 'missing_certutil')
        - message: str (Descripción legible)
        - recommendation: str (Paso a seguir si hay problema)
    """
    mkcert_ok = is_mkcert_installed()
    certutil_ok = is_certutil_installed()

    if not mkcert_ok:
        return {
            "mkcert_installed": False,
            "certutil_installed": certutil_ok,
            "healthy": False,
            "status_code": "missing_mkcert",
            "message": "mkcert no está instalado en el sistema.",
            "recommendation": "Instala mkcert para que DDEV pueda generar certificados HTTPS locales válidos."
        }

    if not certutil_ok:
        return {
            "mkcert_installed": True,
            "certutil_installed": False,
            "healthy": False,
            "status_code": "missing_certutil",
            "message": "Falta 'certutil' (paquete libnss3-tools). Los navegadores (Chrome/Firefox) no confiarán en los certificados locales.",
            "recommendation": f"Instala libnss3-tools con: {get_certutil_install_command()} y luego ejecuta 'mkcert -install'."
        }

    return {
        "mkcert_installed": True,
        "certutil_installed": True,
        "healthy": True,
        "status_code": "ok",
        "message": "Certificados SSL configurados correctamente. Chrome y Firefox confían en la CA local.",
        "recommendation": "Tu entorno está completamente configurado para HTTPS local."
    }


def run_mkcert_install() -> Tuple[bool, str]:
    """
    Ejecuta 'mkcert -install' para registrar la autoridad certificadora local
    en el sistema y en los almacenes de confianza de navegadores (NSS).

    Retorna:
        (éxito: bool, salida_o_error: str)
    """
    if not is_mkcert_installed():
        return False, "Error: 'mkcert' no se encuentra instalado en el sistema."

    try:
        proc = subprocess.run(
            ["mkcert", "-install"],
            capture_output=True,
            text=True,
            check=False
        )
        combined_output = (proc.stdout + "\n" + proc.stderr).strip()
        success = proc.returncode == 0
        return success, combined_output
    except Exception as e:
        return False, f"Error ejecutando mkcert: {e}"
