# -*- coding: utf-8 -*-
"""
Cliente Core y resolvedor para motor de Inteligencia Artificial Local (Ollama).
Completamente desacoplado, sin dependencias externas pesadas (utiliza la biblioteca estándar de Python).
"""

import json
import os
import shutil
import urllib.request
import urllib.error
from typing import Callable, Optional

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_URL = DEFAULT_OLLAMA_HOST

MAX_CONTEXT_FILE_BYTES = 30 * 1024  # 30 KB límite seguro para no saturar la CPU

SUPPORTED_TEXT_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".py", ".php", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".sql", ".sh", ".bash", ".css", ".scss", ".html",
    ".htm", ".xml", ".toml", ".ini", ".conf", ".log", ".env", ".example",
    ".dockerfile", ".gitignore", ".lock"
}


def read_context_file(file_path: str, max_bytes: int = MAX_CONTEXT_FILE_BYTES) -> dict:
    """
    Lee de forma segura un archivo de texto, código fuente, log o Markdown para
    incorporarlo como contexto en el asistente de IA.
    Protege la memoria y la CPU truncando archivos que excedan max_bytes.
    Retorna un diccionario con metadatos y contenido formateado.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"El archivo no existe: {file_path}")

    size_bytes = os.path.getsize(file_path)
    base_name = os.path.basename(file_path)

    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read(max_bytes + 1)
    except Exception as ex:
        raise IOError(f"No se pudo leer el archivo: {ex}")

    is_truncated = len(raw_bytes) > max_bytes
    if is_truncated:
        raw_bytes = raw_bytes[:max_bytes]

    # Detección de archivos binarios (ej. ejecutables, imágenes o paquetes con null bytes)
    if b"\x00" in raw_bytes[:1024]:
        raise ValueError("El archivo seleccionado parece ser binario o ejecutable y no puede ser interpretado como texto.")

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = raw_bytes.decode("latin-1")
        except Exception:
            raise ValueError("El archivo seleccionado parece ser binario y no puede ser interpretado como texto.")

    # Formatear tamaño amigable
    if size_bytes >= 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes} B"

    return {
        "name": base_name,
        "path": file_path,
        "content": content,
        "size_bytes": size_bytes,
        "size_str": size_str,
        "truncated": is_truncated,
    }


def find_and_read_project_doc(project_dir: str, max_bytes: int = 15 * 1024) -> Optional[dict]:
    """
    Busca automáticamente archivos de documentación clave en la raíz de un proyecto
    (PROJECT_CONTEXT.md, README.md, readme.md, etc.) y retorna su contenido seguro
    truncado a max_bytes para alimentar el contexto de la IA sin saturar la CPU.
    """
    if not project_dir or not os.path.isdir(project_dir):
        return None

    candidates = [
        "PROJECT_CONTEXT.md",
        "project_context.md",
        "README.md",
        "readme.md",
        "Readme.md",
        "README.MD",
        "README.markdown",
        "README.txt",
        "readme.txt",
    ]

    for filename in candidates:
        filepath = os.path.join(project_dir, filename)
        if os.path.isfile(filepath):
            try:
                return read_context_file(filepath, max_bytes=max_bytes)
            except Exception:
                continue
    return None



CATALOG_RECOMMENDED_MODELS = [
    {
        "name": "llama3.2:3b",
        "label": "Llama 3.2 (3B)",
        "tagline": "Recomendado general para cualquier consulta, conceptos técnicos y redacción en español",
        "size_str": "2.0 GB",
        "ram_req": "3 GB RAM",
    },
    {
        "name": "qwen2.5:3b",
        "label": "Qwen 2.5 (3B)",
        "tagline": "Excelente en razonamiento técnico, DevOps, redes, comandos y programación",
        "size_str": "2.3 GB",
        "ram_req": "3 GB RAM",
    },
    {
        "name": "qwen2.5-coder:1.5b",
        "label": "Qwen 2.5 Coder (1.5B)",
        "tagline": "Ultra rápido y liviano, ideal para laptops o memoria RAM limitada",
        "size_str": "1.0 GB",
        "ram_req": "2 GB RAM",
    },
    {
        "name": "phi3.5:3.8b",
        "label": "Phi 3.5 (3.8B)",
        "tagline": "Capacidad analítica avanzada de Microsoft para explicaciones profundas y didácticas",
        "size_str": "2.2 GB",
        "ram_req": "3.5 GB RAM",
    },
]


class OllamaClient:
    """Cliente HTTP desacoplado para comunicarse con el servidor local Ollama."""

    def __init__(self, host: str = DEFAULT_OLLAMA_HOST):
        self.host = host.rstrip("/")
        self.base_url = self.host

    def is_binary_installed(self) -> bool:
        """Comprueba si el binario de ollama está presente en el PATH del sistema."""
        return shutil.which("ollama") is not None

    def is_server_running(self, timeout: float = 1.2) -> bool:
        """Comprueba si el servidor local de Ollama está escuchando en el puerto configurado."""
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DDEV-Studio"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None)
                if status is None and hasattr(resp, "getcode"):
                    status = resp.getcode()
                return status == 200
        except Exception:
            return False

    def list_installed_models(self, timeout: float = 2.0) -> list[dict]:
        """Retorna la lista de modelos descargados localmente en Ollama."""
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DDEV-Studio"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None)
                if status is None and hasattr(resp, "getcode"):
                    status = resp.getcode()
                if status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    raw_models = payload.get("models", [])
                    result = []
                    for m in raw_models:
                        name = m.get("name", "")
                        size_bytes = m.get("size", 0)
                        size_mb = size_bytes / (1024 * 1024)
                        size_str = f"{size_mb / 1024:.1f} GB" if size_mb >= 1024 else f"{size_mb:.0f} MB"
                        result.append({
                            "name": name,
                            "size_bytes": size_bytes,
                            "size_str": size_str,
                            "modified_at": m.get("modified_at", ""),
                        })
                    return result
        except Exception:
            pass
        return []

    def get_running_models_info(self, timeout: float = 1.5) -> list[dict]:
        """
        Retorna la lista detallada de modelos activos en memoria RAM/VRAM en Ollama
        junto con su tamaño en bytes y cadena formateada de consumo de memoria.
        """
        url = f"{self.host}/api/ps"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DDEV-Studio"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None)
                if status is None and hasattr(resp, "getcode"):
                    status = resp.getcode()
                if status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    raw_models = payload.get("models", [])
                    result = []
                    for m in raw_models:
                        name = m.get("name", "")
                        size_bytes = m.get("size", 0)
                        size_vram = m.get("size_vram", 0)
                        size_mb = size_bytes / (1024 * 1024)
                        size_str = f"{size_mb / 1024:.1f} GB" if size_mb >= 1024 else f"{size_mb:.0f} MB"
                        result.append({
                            "name": name,
                            "size_bytes": size_bytes,
                            "size_vram": size_vram,
                            "size_str": size_str,
                            "expires_at": m.get("expires_at", ""),
                        })
                    return result
        except Exception:
            pass
        return []

    def get_running_models(self, timeout: float = 1.5) -> list[str]:
        """
        Retorna la lista de nombres de modelos que actualmente se encuentran
        cargados y activos en memoria RAM/VRAM en Ollama (consultando /api/ps).
        """
        info = self.get_running_models_info(timeout=timeout)
        return [m["name"] for m in info if m.get("name")]

    def is_model_loaded(self, model_name: str, timeout: float = 1.5) -> bool:
        """
        Determina si un modelo ya está cargado en memoria RAM/VRAM (Warm State).
        Si no lo está, una consulta provocará un arranque en frío (Cold Start).
        """
        if not model_name:
            return False
        running = self.get_running_models(timeout=timeout)
        target_clean = model_name.split(":")[0].strip()
        for m in running:
            if m == model_name or m.split(":")[0].strip() == target_clean:
                return True
        return False

    def unload_model(self, model_name: str, timeout: float = 5.0) -> bool:
        """
        Descarga inmediatamente un modelo de la memoria RAM/VRAM en Ollama (keep_alive: 0).
        Libera instantáneamente la CPU y memoria del sistema.
        """
        if not model_name:
            return False
        url = f"{self.host}/api/generate"
        payload = json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "DDEV-Studio"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None)
                if status is None and hasattr(resp, "getcode"):
                    status = resp.getcode()
                return status == 200
        except Exception:
            return False

    def get_install_command(self, use_pkexec: bool = True) -> list[str]:
        """Retorna el comando recomendado para instalar Ollama en Linux."""
        script_cmd = "curl -fsSL https://ollama.com/install.sh | sh"
        if use_pkexec and shutil.which("pkexec"):
            return ["pkexec", "bash", "-c", script_cmd]
        return ["bash", "-c", script_cmd]

    def get_start_command(self) -> list[str]:
        """Retorna el comando para iniciar el servicio systemd de Ollama."""
        return ["systemctl", "start", "ollama"]

    def pull_model_stream(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[dict], None]] = None,
        cancel_event=None
    ) -> bool:
        """
        Descarga un modelo desde el registro de Ollama reportando el progreso en tiempo real.
        """
        url = f"{self.host}/api/pull"
        payload = json.dumps({"name": model_name, "stream": True}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "DDEV-Studio"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3600) as resp:
                for raw_line in resp:
                    if cancel_event and cancel_event.is_set():
                        return False
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if progress_callback:
                            progress_callback(data)
                        if data.get("status") == "success":
                            return True
                    except json.JSONDecodeError:
                        continue
                return True
        except Exception as ex:
            if progress_callback:
                progress_callback({"status": f"Error: {ex}", "error": True})
            return False

    def chat_stream(
        self,
        model_name: str,
        messages: list[dict],
        system_prompt: str = "",
        chunk_callback: Optional[Callable[[str], None]] = None,
        cancel_event=None,
        timeout: float = 120.0
    ) -> str:
        """
        Envía un historial de mensajes a Ollama y transmite los fragmentos generados en tiempo real.
        Retorna la respuesta acumulada completa.
        """
        url = f"{self.host}/api/chat"
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        payload = json.dumps({
            "model": model_name,
            "messages": all_messages,
            "stream": True,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "DDEV-Studio"},
            method="POST",
        )

        full_response = []
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for raw_line in resp:
                    if cancel_event and cancel_event.is_set():
                        break
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg = data.get("message", {})
                        chunk = msg.get("content", "")
                        if chunk:
                            full_response.append(chunk)
                            if chunk_callback:
                                chunk_callback(chunk)
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as ex:
            err_msg = f"\n[Error de comunicación con Ollama: {ex}]"
            full_response.append(err_msg)
            if chunk_callback:
                chunk_callback(err_msg)

        return "".join(full_response)
