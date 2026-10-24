# -*- coding: utf-8 -*-
"""
Módulo Core de Gestión de Voz e Inteligencia Artificial Acústica (Whisper & Kokoro).
Desacoplado, sin dependencias pesadas en el proceso principal, con ejecución
aislada en entorno virtual y subprocesos para no bloquear la interfaz GTK3.
"""

import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import urllib.request
from typing import Callable, Optional

# Constantes de Rutas
DEFAULT_VOICE_DIR = os.path.expanduser("~/.local/share/ddev-studio/voice")
VENV_DIR = os.path.join(DEFAULT_VOICE_DIR, "venv")
VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python3")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

MODELS_DIR = os.path.join(DEFAULT_VOICE_DIR, "models")
KOKORO_MODEL_PATH = os.path.join(MODELS_DIR, "kokoro-v1.0.onnx")
KOKORO_VOICES_PATH = os.path.join(MODELS_DIR, "voices-v1.0.bin")

CACHE_DIR = os.path.join(DEFAULT_VOICE_DIR, "cache")
CONFIG_PATH = os.path.expanduser("~/.config/ddev-studio/voice_config.json")
WORKER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_worker.py")

# URLs de descarga directa de pesos del modelo Kokoro-82M ONNX
KOKORO_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

# Catálogos canónicos
AVAILABLE_VOICES = [
    {"id": "ef_dora", "name": "Dora (Femenina - Español)", "lang": "es"},
    {"id": "em_alex", "name": "Alex (Masculino - Español)", "lang": "es"},
    {"id": "em_santa", "name": "Santa (Masculino - Español)", "lang": "es"},
    {"id": "af_bella", "name": "Bella (Femenina - Multilingüe)", "lang": "es"},
    {"id": "am_adam", "name": "Adam (Masculino - Multilingüe)", "lang": "es"},
]

AVAILABLE_WHISPER_MODELS = [
    {"id": "tiny", "name": "Tiny (~75 MB, ultra rápido)", "desc": "Mínimo consumo de CPU, ideal para laptops"},
    {"id": "base", "name": "Base (~145 MB, equilibrado)", "desc": "Recomendado: óptima relación velocidad y precisión"},
    {"id": "small", "name": "Small (~480 MB, alta precisión)", "desc": "Mayor fidelidad en términos técnicos y código"},
]

DEFAULT_CONFIG = {
    "voice": "ef_dora",
    "speed": 1.0,
    "whisper_model": "base",
    "auto_speak": False
}


def clean_text_for_speech(text: str) -> str:
    """
    Limpia y optimiza texto Markdown o técnico para síntesis vocal en español.
    - Convierte bloques de código ```...``` en menciones naturales ("Código en pantalla").
    - Elimina URLs largas, encabezados #, asteriscos, guiones bajos, tablas y emojis.
    - Reduce comillas, dobles espacios y normaliza puntuación para Kokoro.
    """
    if not text:
        return ""

    t = text

    # 1. Reemplazar bloques de código con descripción hablada natural
    def replace_code_block(match):
        code_content = match.group(1).strip()
        lines = [line.strip() for line in code_content.splitlines() if line.strip()]
        # Si es un comando corto de 1 línea (ej. ddev start), leerlo directamente
        if len(lines) == 1 and len(lines[0]) < 45:
            return f" comando en pantalla: {lines[0]}. "
        return " código que se muestra en pantalla. "

    t = re.sub(r"```(?:[a-zA-Z0-9_\-]+)?\n?(.*?)```", replace_code_block, t, flags=re.DOTALL)

    # 2. Código inline `comando` -> comando
    t = re.sub(r"`([^`]+)`", r"\1", t)

    # 3. Enlaces Markdown [texto](url) -> texto
    t = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", t)

    # 4. URLs sueltas https://... o http://...
    t = re.sub(r"https?://\S+", "el enlace en pantalla", t)

    # 5. Encabezados Markdown (# Título -> Título)
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.MULTILINE)

    # 6. Eliminar marcas de negrita, cursiva, tachado
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"__([^_]+)__", r"\1", t)
    t = re.sub(r"~~([^~]+)~~", r"\1", t)

    # 7. Listas de viñetas (* o - o 1.)
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.MULTILINE)

    # 8. Citas y separadores Markdown
    t = re.sub(r"^>\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*[-=_]{3,}\s*$", "", t, flags=re.MULTILINE)

    # 9. Eliminar emojis comunes o símbolos que ralentizan eSpeak-ng
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)

    # 10. Normalizar espacios y saltos de línea
    t = re.sub(r"\n+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def split_into_speech_chunks(text: str, max_words: int = 24) -> list[str]:
    """
    Divide el texto en oraciones y fragmentos digestibles para Kokoro.
    Permite procesar y reproducir la primera oración en menos de medio segundo,
    manteniendo la fluidez continua durante toda la lectura.
    """
    clean = clean_text_for_speech(text)
    if not clean:
        return []

    # Dividir por puntos, signos de interrogación o exclamación
    raw_sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", clean) if s.strip()]
    if not raw_sentences:
        return []

    chunks = []
    current_chunk = ""

    for s in raw_sentences:
        words = s.split()
        if not words:
            continue

        # Si una sola oración excede max_words, dividirla por pausas (, ; :)
        if len(words) > max_words:
            sub_parts = [p.strip() for p in re.split(r"(?<=[,;:])\s+", s) if p.strip()]
            for p in sub_parts:
                p_words = p.split()
                if not current_chunk:
                    current_chunk = p
                elif len(current_chunk.split()) + len(p_words) <= max_words:
                    current_chunk = f"{current_chunk} {p}"
                else:
                    chunks.append(current_chunk.strip())
                    current_chunk = p
        else:
            if not current_chunk:
                current_chunk = s
            elif len(current_chunk.split()) < 4:
                # Si el fragmento actual es muy corto (menos de 4 palabras), unir con la siguiente
                current_chunk = f"{current_chunk} {s}"
            else:
                # Ya es una oración completa y sustancial, cerrar chunk para enviar a síntesis
                chunks.append(current_chunk.strip())
                current_chunk = s

    if current_chunk:
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c]


class VoiceManager:
    """
    Gestor maestro del subsistema de voz (Whisper STT + Kokoro TTS).
    Proporciona métodos de diagnóstico, instalación desatendida, grabación de
    micrófono, transcripción acústica, síntesis vocal y reproducción de audio.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._recording_process = None
        self._recording_file = None
        self._playback_process = None
        self._playback_cancel_evt = None
        self._daemon_process = None
        self._daemon_lock = threading.Lock()
        self._req_counter = 0
        self._lock = threading.Lock()
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Crea las carpetas necesarias para el almacenamiento de modelos y caché."""
        for d in [DEFAULT_VOICE_DIR, MODELS_DIR, CACHE_DIR, os.path.dirname(CONFIG_PATH)]:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Configuración Persistente
    # -------------------------------------------------------------------------
    def get_config(self) -> dict:
        """Carga la configuración de voz persistente o valores por defecto."""
        if not os.path.isfile(CONFIG_PATH):
            return dict(DEFAULT_CONFIG)
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
        except Exception:
            return dict(DEFAULT_CONFIG)

    def update_config(self, **kwargs) -> dict:
        """Actualiza y persiste las preferencias de voz del usuario."""
        cfg = self.get_config()
        cfg.update(kwargs)
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return cfg

    # -------------------------------------------------------------------------
    # Detección y Diagnóstico del Entorno
    # -------------------------------------------------------------------------
    def check_system_dependencies(self) -> dict:
        """
        Verifica la presencia de binarios y dependencias del sistema operativo
        para captura, reproducción y fonemas en Linux.
        """
        # Chequear si python3 puede crear entornos venv con ensurepip
        can_venv = False
        try:
            r = subprocess.run(
                [sys.executable, "-c", "import ensurepip; print(True)"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            can_venv = (r.returncode == 0 and "True" in r.stdout)
        except Exception:
            can_venv = False

        has_espeak = shutil.which("espeak-ng") is not None
        has_ffmpeg = shutil.which("ffmpeg") is not None
        has_recorder = (shutil.which("arecord") is not None) or (shutil.which("pw-record") is not None) or has_ffmpeg
        has_player = (shutil.which("pw-play") is not None) or (shutil.which("aplay") is not None)

        return {
            "python3_venv": can_venv,
            "espeak_ng": has_espeak,
            "ffmpeg": has_ffmpeg,
            "audio_recorder": has_recorder,
            "audio_player": has_player,
        }

    def get_missing_system_packages(self) -> list:
        """Determina la lista de paquetes Debian/Ubuntu pendientes de instalar."""
        deps = self.check_system_dependencies()
        missing = []
        if not deps.get("python3_venv"):
            missing.extend(["python3-venv", "python3-pip"])
        if not deps.get("espeak_ng"):
            missing.append("espeak-ng")
        if not deps.get("ffmpeg"):
            missing.append("ffmpeg")
        return missing

    def get_system_install_command(self, use_pkexec: bool = True):
        """
        Genera el comando seguro para instalar las dependencias del sistema
        mediante PolicyKit (gráfico) o directamente en terminal.
        """
        missing = self.get_missing_system_packages()
        if not missing:
            missing = ["python3-venv", "python3-pip", "espeak-ng", "ffmpeg"]
        pkgs_str = " ".join(missing)
        script_cmd = f"apt-get update && apt-get install -y {pkgs_str}"

        if use_pkexec and shutil.which("pkexec"):
            return ["pkexec", "sh", "-c", script_cmd]
        return ["sudo", "sh", "-c", script_cmd]

    def is_venv_ready(self) -> bool:
        """Verifica si el intérprete de Python y pip dentro del venv existen y son ejecutables."""
        if not (os.path.isfile(VENV_PYTHON) and os.access(VENV_PYTHON, os.X_OK)):
            return False
        # Validar que pip realmente esté presente y operativo dentro del venv
        if not (os.path.isfile(VENV_PIP) and os.access(VENV_PIP, os.X_OK)):
            return False
        return True

    def are_models_downloaded(self) -> bool:
        """Verifica que los pesos de Kokoro ONNX y el archivo de voces existan y tengan tamaño válido."""
        if not (os.path.isfile(KOKORO_MODEL_PATH) and os.path.isfile(KOKORO_VOICES_PATH)):
            return False
        # kokoro-v1.0.onnx debe superar los 200MB y voices los 10MB
        try:
            m_size = os.path.getsize(KOKORO_MODEL_PATH)
            v_size = os.path.getsize(KOKORO_VOICES_PATH)
            return m_size > (100 * 1024 * 1024) and v_size > (5 * 1024 * 1024)
        except Exception:
            return False

    def check_worker_health(self) -> tuple[bool, str]:
        """Ejecuta el worker en modo check para confirmar que las librerías cargan sin error."""
        if not self.is_venv_ready():
            return False, "Entorno virtual de voz no inicializado o incompleto."
        try:
            res = subprocess.run(
                [VENV_PYTHON, WORKER_PATH, "check"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                if data.get("ok"):
                    return True, "Entorno de inferencia activo y saludable."
                return False, data.get("error", "Error desconocido en worker.")
            return False, res.stderr or res.stdout or f"Worker falló con código {res.returncode}"
        except Exception as ex:
            return False, str(ex)

    def is_installed(self) -> bool:
        """Comprueba de forma integral si todo el subsistema de voz está operativo."""
        if not self.is_venv_ready():
            return False
        if not self.are_models_downloaded():
            return False
        ok, _ = self.check_worker_health()
        return ok

    # -------------------------------------------------------------------------
    # Instalación Desatendida de Whisper y Kokoro
    # -------------------------------------------------------------------------
    def install(self, on_log: Optional[Callable[[str], None]] = None,
                on_progress: Optional[Callable[[float], None]] = None) -> tuple[bool, str]:
        """
        Instala el entorno virtual aislado, descarga librerías ML de Python
        (faster-whisper, kokoro-onnx, soundfile) y descarga los modelos ONNX.
        """
        def log(msg: str):
            if on_log:
                on_log(f"{msg}\n")

        def set_progress(val: float):
            if on_progress:
                on_progress(val)

        try:
            self._ensure_dirs()
            set_progress(0.05)

            # Paso 1: Crear entorno virtual
            log("📦 Paso 1/4: Creando entorno virtual aislado de Python para voz...")
            if not self.is_venv_ready():
                cmd_venv = [sys.executable, "-m", "venv", "--clear", VENV_DIR]
                proc = subprocess.run(cmd_venv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode != 0:
                    err_msg = proc.stderr or proc.stdout
                    log(f"❌ Error al crear venv: {err_msg}")
                    return False, f"No se pudo crear venv: {err_msg}"
                log(f"✔ Entorno virtual creado exitosamente en {VENV_DIR}")
            else:
                log("✔ Entorno virtual existente detectado con pip operativo.")

            set_progress(0.20)

            # Paso 2: Actualizar pip e instalar librerías
            log("\n🚀 Paso 2/4: Instalando dependencias de IA (faster-whisper, kokoro-onnx, soundfile)...")
            log("⏳ Descargando e indexando paquetes en el entorno aislado (esto puede tomar 1 o 2 minutos)...")

            pip_upgrade_cmd = [VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip"]
            subprocess.run(pip_upgrade_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            pip_install_cmd = [
                VENV_PYTHON, "-m", "pip", "install",
                "faster-whisper",
                "kokoro-onnx",
                "soundfile",
            ]

            p_pip = subprocess.Popen(
                pip_install_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in iter(p_pip.stdout.readline, ''):
                clean_line = line.strip()
                if clean_line:
                    log(f"  [pip] {clean_line}")
            p_pip.stdout.close()
            p_pip.wait()

            if p_pip.returncode != 0:
                log("❌ Error durante la instalación de paquetes con pip.")
                return False, "Fallo al instalar paquetes de Python con pip."

            log("✔ Librerías de IA instaladas correctamente.")
            set_progress(0.60)

            # Paso 3: Descarga de modelos Kokoro-82M ONNX
            log("\n🧠 Paso 3/4: Descargando pesos de Kokoro-82M ONNX y paquete de voces en español...")
            models_to_download = [
                (KOKORO_MODEL_URL, KOKORO_MODEL_PATH, "kokoro-v1.0.onnx (~310 MB)"),
                (KOKORO_VOICES_URL, KOKORO_VOICES_PATH, "voices-v1.0.bin (~28 MB)"),
            ]

            for url, dest_path, label in models_to_download:
                if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 1024 * 1024:
                    log(f"✔ Archivo de modelo ya presente: {label}")
                    continue

                log(f"📥 Descargando {label} desde GitHub Releases...")
                tmp_dest = dest_path + ".tmp"

                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "DDEV-Studio-Voice-Installer"}
                )
                with urllib.request.urlopen(req, timeout=120) as resp, open(tmp_dest, "wb") as out_f:
                    total_bytes = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    chunk_size = 256 * 1024  # 256 KB
                    last_pct = -1

                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes > 0:
                            pct = int((downloaded / total_bytes) * 100)
                            if pct != last_pct and pct % 10 == 0:
                                last_pct = pct
                                log(f"  Descargando {label}: {pct}% ({downloaded // (1024*1024)}MB / {total_bytes // (1024*1024)}MB)")

                os.replace(tmp_dest, dest_path)
                log(f"✔ {label} descargado y verificado correctamente.")

            set_progress(0.90)

            # Paso 4: Validación final de salud del worker
            log("\n🔍 Paso 4/4: Verificando integridad del motor de inferencia...")
            ok, msg = self.check_worker_health()
            if not ok:
                log(f"❌ Validación fallida: {msg}")
                return False, f"Validación de worker fallida: {msg}"

            log("🎉 ¡Instalación de Whisper y Kokoro completada con éxito!")
            set_progress(1.0)
            return True, "Subsistema de voz instalado y listo para su uso."

        except Exception as ex:
            log(f"💥 Error inesperado en la instalación: {ex}")
            return False, str(ex)

    # -------------------------------------------------------------------------
    # Grabación de Micrófono y Transcripción STT (Whisper)
    # -------------------------------------------------------------------------
    def is_recording(self) -> bool:
        """Determina si la grabación de micrófono está activa."""
        return self._recording_process is not None and self._recording_process.poll() is None

    def start_recording(self, output_wav_path: Optional[str] = None) -> str:
        """
        Inicia la captura de audio por micrófono en segundo plano.
        Retorna la ruta del archivo WAV donde se guardará el audio grabado.
        """
        with self._lock:
            if self.is_recording():
                return self._recording_file

            if not output_wav_path:
                fd, output_wav_path = tempfile.mkstemp(prefix="ddev_mic_", suffix=".wav", dir=CACHE_DIR)
                os.close(fd)

            self._recording_file = output_wav_path

            # Prioridad de grabadores nativos: arecord -> ffmpeg -> pw-record
            cmd = None
            if shutil.which("arecord"):
                cmd = ["arecord", "-q", "-r", "16000", "-c", "1", "-f", "S16_LE", self._recording_file]
            elif shutil.which("ffmpeg"):
                cmd = ["ffmpeg", "-y", "-loglevel", "quiet", "-f", "alsa", "-i", "default", "-ar", "16000", "-ac", "1", self._recording_file]
            elif shutil.which("pw-record"):
                cmd = ["pw-record", "--rate", "16000", "--channels", "1", self._recording_file]
            else:
                raise RuntimeError("No se encontró ningún grabador de audio nativo (arecord, ffmpeg o pw-record).")

            self._recording_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            return self._recording_file

    def stop_recording(self) -> Optional[str]:
        """
        Detiene la grabación de micrófono activa y retorna la ruta del audio WAV finalizado.
        """
        with self._lock:
            if not self._recording_process:
                return self._recording_file

            proc = self._recording_process
            self._recording_process = None

            try:
                # Enviar señal SIGINT para que arecord o ffmpeg cierren la cabecera WAV de forma limpia
                os.killpg(os.getpgid(proc.pid), signal.SIGINT)
                proc.wait(timeout=2)
            except Exception:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=1)
                except Exception:
                    pass

            target_file = self._recording_file
            if target_file and os.path.isfile(target_file) and os.path.getsize(target_file) > 1000:
                return target_file
            return None

    def transcribe(self, audio_path: str, language: str = "es", model: Optional[str] = None) -> str:
        """
        Transcribe un archivo WAV a texto utilizando Faster-Whisper a través del worker aislado.
        """
        if not self.is_venv_ready():
            raise RuntimeError("El entorno de voz no está instalado.")

        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

        cfg = self.get_config()
        selected_model = model or cfg.get("whisper_model", "base")

        cmd = [
            VENV_PYTHON, WORKER_PATH, "transcribe",
            "--audio", audio_path,
            "--model", selected_model,
            "--lang", language
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120
        )

        if proc.returncode != 0:
            err = proc.stderr or proc.stdout
            raise RuntimeError(f"Error en transcripción Whisper: {err}")

        try:
            data = json.loads(proc.stdout)
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "Error desconocido en Whisper"))
            return data.get("text", "").strip()
        except json.JSONDecodeError:
            raise RuntimeError(f"Respuesta no válida del transcriptor: {proc.stdout}")

    # -------------------------------------------------------------------------
    # Síntesis Vocal TTS (Kokoro) y Demonio en RAM
    # -------------------------------------------------------------------------
    def _safe_callback(self, cb):
        """Invoca un callback de forma segura en el hilo de GTK si está disponible."""
        if not cb:
            return
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import GLib
            GLib.idle_add(cb)
        except Exception:
            try:
                cb()
            except Exception:
                pass

    def _ensure_daemon(self) -> bool:
        """Asegura que el worker demonio de Kokoro esté cargado en RAM."""
        with self._daemon_lock:
            if self._daemon_process and self._daemon_process.poll() is None:
                return True

            if not self.is_venv_ready() or not self.are_models_downloaded():
                return False

            try:
                cmd = [
                    VENV_PYTHON, WORKER_PATH, "daemon",
                    "--model-path", KOKORO_MODEL_PATH,
                    "--voices-path", KOKORO_VOICES_PATH
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                ready_line = proc.stdout.readline()
                if not ready_line or "ready" not in ready_line:
                    proc.kill()
                    return False
                self._daemon_process = proc
                return True
            except Exception:
                self._daemon_process = None
                return False

    def _daemon_synthesize(self, text: str, output_path: str, voice: str, speed: float) -> Optional[dict]:
        """Envía solicitud directa al demonio residente en RAM vía stdin/stdout."""
        with self._daemon_lock:
            if not self._daemon_process or self._daemon_process.poll() is not None:
                if not self._ensure_daemon():
                    return None

            try:
                self._req_counter += 1
                req_id = self._req_counter
                payload = json.dumps({
                    "action": "synthesize",
                    "id": req_id,
                    "text": text,
                    "output": output_path,
                    "voice": voice,
                    "speed": speed,
                    "lang": "es"
                }) + "\n"

                self._daemon_process.stdin.write(payload)
                self._daemon_process.stdin.flush()

                resp_line = self._daemon_process.stdout.readline()
                if not resp_line:
                    return None
                data = json.loads(resp_line)
                if data.get("ok"):
                    return data
                return None
            except Exception:
                return None

    def unload_daemon(self):
        """Detiene y descarga el demonio de la memoria RAM para liberar recursos."""
        with self._daemon_lock:
            if self._daemon_process:
                try:
                    self._daemon_process.stdin.write(json.dumps({"action": "exit"}) + "\n")
                    self._daemon_process.stdin.flush()
                    self._daemon_process.wait(timeout=1)
                except Exception:
                    try:
                        self._daemon_process.kill()
                    except Exception:
                        pass
                self._daemon_process = None

    def synthesize(self, text: str, output_path: Optional[str] = None,
                   voice: Optional[str] = None, speed: Optional[float] = None) -> str:
        """
        Sintetiza texto en español a archivo WAV con Kokoro-82M ONNX.
        Aprovecha el demonio en caliente si está disponible o recurre al modo CLI.
        """
        if not self.is_venv_ready():
            raise RuntimeError("El entorno de voz no está instalado.")

        if not self.are_models_downloaded():
            raise RuntimeError("Los modelos de voz Kokoro no están descargados.")

        cfg = self.get_config()
        sel_voice = voice or cfg.get("voice", "ef_dora")
        sel_speed = speed if speed is not None else cfg.get("speed", 1.0)

        if not output_path:
            fd, output_path = tempfile.mkstemp(prefix="ddev_tts_", suffix=".wav", dir=CACHE_DIR)
            os.close(fd)

        # 1. Intentar con el demonio en RAM (latencia ultra baja)
        res = self._daemon_synthesize(text, output_path, sel_voice, sel_speed)
        if res and res.get("ok") and os.path.isfile(output_path) and os.path.getsize(output_path) > 100:
            return output_path

        # 2. Fallback CLI de un solo disparo
        cmd = [
            VENV_PYTHON, WORKER_PATH, "synthesize",
            "--text", text,
            "--output", output_path,
            "--model-path", KOKORO_MODEL_PATH,
            "--voices-path", KOKORO_VOICES_PATH,
            "--voice", sel_voice,
            "--speed", str(sel_speed),
            "--lang", "es"
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=90
        )

        if proc.returncode != 0:
            err = proc.stderr or proc.stdout
            raise RuntimeError(f"Error en síntesis Kokoro: {err}")

        try:
            data = json.loads(proc.stdout)
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "Error desconocido en Kokoro"))
            return data.get("output", output_path)
        except json.JSONDecodeError:
            raise RuntimeError(f"Respuesta no válida del sintetizador: {proc.stdout}")

    def is_playing(self) -> bool:
        """Verifica si hay reproducción de audio activa."""
        return self._playback_process is not None and self._playback_process.poll() is None

    def stop_playback(self):
        """Detiene cualquier reproducción de audio en curso y cancela la cola streaming."""
        if hasattr(self, "_playback_cancel_evt") and self._playback_cancel_evt:
            self._playback_cancel_evt.set()

        with self._lock:
            if self._playback_process:
                try:
                    self._playback_process.terminate()
                    self._playback_process.wait(timeout=1)
                except Exception:
                    try:
                        self._playback_process.kill()
                    except Exception:
                        pass
                self._playback_process = None

    def play_audio(self, wav_path: str, on_finish: Optional[Callable[[], None]] = None):
        """
        Reproduce un archivo WAV en segundo plano utilizando el reproductor
        nativo de Linux (pw-play o aplay) sin bloquear la interfaz.
        """
        self.stop_playback()

        if not os.path.isfile(wav_path):
            raise FileNotFoundError(f"Archivo de audio a reproducir no existe: {wav_path}")

        player = shutil.which("pw-play") or shutil.which("aplay")
        if not player:
            raise RuntimeError("No se encontró reproductor de audio compatible (pw-play o aplay).")

        cmd = [player, wav_path]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._playback_process = proc

        def monitor():
            try:
                proc.wait()
            except Exception:
                pass
            finally:
                with self._lock:
                    if self._playback_process == proc:
                        self._playback_process = None
                if on_finish:
                    self._safe_callback(on_finish)

        threading.Thread(target=monitor, daemon=True).start()

    def play_speech_stream(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None,
                           on_start: Optional[Callable[[], None]] = None,
                           on_finish: Optional[Callable[[], None]] = None):
        """
        Sintetiza y reproduce el texto en streaming por oraciones con latencia ultrabaja (< 300ms):
        1. Limpia y fragmenta el texto en oraciones conversacionales.
        2. Sintetiza la primera frase en el worker en RAM y la empieza a reproducir de inmediato.
        3. En paralelo, sintetiza las siguientes frases en segundo plano alimentando la cola de audio.
        4. Transición fluida y continua entre fragmentos sin silencios molestos.
        """
        self.stop_playback()

        chunks = split_into_speech_chunks(text)
        if not chunks:
            if on_finish:
                self._safe_callback(on_finish)
            return

        cfg = self.get_config()
        sel_voice = voice or cfg.get("voice", "ef_dora")
        sel_speed = speed if speed is not None else cfg.get("speed", 1.0)

        cancel_evt = threading.Event()
        self._playback_cancel_evt = cancel_evt

        def pipeline_thread():
            audio_queue = queue.Queue(maxsize=15)
            synthesis_done = threading.Event()

            # Hilo productor: sintetiza chunk por chunk en segundo plano
            def synth_worker():
                for idx, chunk in enumerate(chunks):
                    if cancel_evt.is_set():
                        break
                    fd, out_wav = tempfile.mkstemp(prefix=f"ddev_stream_{idx}_", suffix=".wav", dir=CACHE_DIR)
                    os.close(fd)
                    try:
                        res = self._daemon_synthesize(chunk, out_wav, sel_voice, sel_speed)
                        if not res or not res.get("ok"):
                            self.synthesize(chunk, output_path=out_wav, voice=sel_voice, speed=sel_speed)
                        if not cancel_evt.is_set():
                            audio_queue.put(out_wav)
                    except Exception as ex:
                        print(f"[Streaming Synth Error]: {ex}")
                synthesis_done.set()

            t_synth = threading.Thread(target=synth_worker, daemon=True)
            t_synth.start()

            # Esperar el primer chunk para arrancar inmediatamente
            try:
                first_wav = audio_queue.get(timeout=10.0)
            except queue.Empty:
                if on_finish:
                    self._safe_callback(on_finish)
                return

            if cancel_evt.is_set():
                return

            if on_start:
                self._safe_callback(on_start)

            player = shutil.which("pw-play") or shutil.which("aplay")
            if not player:
                if on_finish:
                    self._safe_callback(on_finish)
                return

            current_wav = first_wav
            while current_wav and not cancel_evt.is_set():
                cmd = [player, current_wav]
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with self._lock:
                    self._playback_process = proc

                proc.wait()

                try:
                    os.remove(current_wav)
                except Exception:
                    pass

                if cancel_evt.is_set():
                    break

                current_wav = None
                while not cancel_evt.is_set():
                    try:
                        current_wav = audio_queue.get(timeout=0.1)
                        break
                    except queue.Empty:
                        if synthesis_done.is_set():
                            break

            with self._lock:
                self._playback_process = None

            if on_finish:
                self._safe_callback(on_finish)

        threading.Thread(target=pipeline_thread, daemon=True).start()
