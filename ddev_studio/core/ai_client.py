# -*- coding: utf-8 -*-
"""
Cliente Core y resolvedor para motor de Inteligencia Artificial Local (Ollama).
Completamente desacoplado, sin dependencias externas pesadas (utiliza la biblioteca estándar de Python).
"""

import json
import shutil
import urllib.request
import urllib.error
from typing import Callable, Optional

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_URL = DEFAULT_OLLAMA_HOST

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
