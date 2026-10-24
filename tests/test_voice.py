# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el módulo de voz con IA (Whisper & Kokoro) en DDEV Studio.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.core.voice import (
    VoiceManager,
    AVAILABLE_VOICES,
    AVAILABLE_WHISPER_MODELS,
    DEFAULT_CONFIG,
    DEFAULT_VOICE_DIR,
)


class TestVoiceManager(unittest.TestCase):

    def setUp(self):
        # Reset singleton state for clean testing
        VoiceManager._instance = None
        self.mgr = VoiceManager()

    def test_catalog_definitions(self):
        """Verifica que los catálogos de voces en español y modelos Whisper estén bien definidos."""
        self.assertGreater(len(AVAILABLE_VOICES), 0)
        voice_ids = [v["id"] for v in AVAILABLE_VOICES]
        self.assertIn("ef_dora", voice_ids)
        self.assertIn("em_alex", voice_ids)

        model_ids = [m["id"] for m in AVAILABLE_WHISPER_MODELS]
        self.assertIn("tiny", model_ids)
        self.assertIn("base", model_ids)

    def test_configuration_defaults_and_updates(self):
        """Verifica la carga y actualización de configuración en archivo temporal."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            custom_cfg_path = os.path.join(tmp_dir, "test_voice_cfg.json")
            with patch("ddev_studio.core.voice.CONFIG_PATH", custom_cfg_path):
                cfg = self.mgr.get_config()
                self.assertEqual(cfg.get("voice"), "ef_dora")
                self.assertEqual(cfg.get("speed"), 1.0)
                self.assertEqual(cfg.get("whisper_model"), "base")
                self.assertFalse(cfg.get("auto_speak"))

                # Actualizar configuración
                updated = self.mgr.update_config(voice="em_alex", speed=1.2, auto_speak=True)
                self.assertEqual(updated.get("voice"), "em_alex")
                self.assertEqual(updated.get("speed"), 1.2)
                self.assertTrue(updated.get("auto_speak"))

                # Re-leer
                read_again = self.mgr.get_config()
                self.assertEqual(read_again.get("voice"), "em_alex")

    @patch("shutil.which")
    def test_check_system_dependencies(self, mock_which):
        """Verifica la detección de utilidades de grabación, reproducción y fonemas."""
        def fake_which(cmd):
            if cmd in ["arecord", "aplay", "espeak-ng", "ffmpeg"]:
                return f"/usr/bin/{cmd}"
            return None

        mock_which.side_effect = fake_which
        deps = self.mgr.check_system_dependencies()
        self.assertTrue(deps["espeak_ng"])
        self.assertTrue(deps["ffmpeg"])
        self.assertTrue(deps["audio_recorder"])
        self.assertTrue(deps["audio_player"])

    @patch.object(VoiceManager, "check_system_dependencies")
    def test_get_missing_system_packages(self, mock_deps):
        """Verifica que determine correctamente qué paquetes de apt faltan."""
        mock_deps.return_value = {
            "python3_venv": False,
            "espeak_ng": False,
            "ffmpeg": True,
            "audio_recorder": True,
            "audio_player": True,
        }
        missing = self.mgr.get_missing_system_packages()
        self.assertIn("python3-venv", missing)
        self.assertIn("python3-pip", missing)
        self.assertIn("espeak-ng", missing)
        self.assertNotIn("ffmpeg", missing)

    @patch("shutil.which")
    def test_get_system_install_command(self, mock_which):
        """Verifica la construcción del comando con pkexec o sudo."""
        mock_which.return_value = "/usr/bin/pkexec"
        cmd = self.mgr.get_system_install_command(use_pkexec=True)
        self.assertEqual(cmd[0], "pkexec")
        self.assertIn("apt-get install", cmd[3])

        cmd_sudo = self.mgr.get_system_install_command(use_pkexec=False)
        self.assertEqual(cmd_sudo[0], "sudo")

    @patch("os.path.isfile")
    @patch("os.access")
    def test_is_venv_ready(self, mock_access, mock_isfile):
        """Verifica comprobación del binario Python del venv."""
        mock_isfile.return_value = True
        mock_access.return_value = True
        self.assertTrue(self.mgr.is_venv_ready())

        mock_isfile.return_value = False
        self.assertFalse(self.mgr.is_venv_ready())

    @patch("os.path.isfile")
    @patch("os.path.getsize")
    def test_are_models_downloaded(self, mock_getsize, mock_isfile):
        """Verifica comprobación de existencia y tamaño mínimo de los modelos Kokoro."""
        mock_isfile.return_value = True
        # Tamaño superior al umbral
        mock_getsize.side_effect = [150 * 1024 * 1024, 10 * 1024 * 1024]
        self.assertTrue(self.mgr.are_models_downloaded())

        # Tamaño inferior (archivo corrupto o vacío)
        mock_getsize.side_effect = [500, 500]
        self.assertFalse(self.mgr.are_models_downloaded())

    @patch("subprocess.Popen")
    @patch("shutil.which")
    def test_recording_lifecycle(self, mock_which, mock_popen):
        """Verifica el ciclo de vida de captura de audio (start_recording y stop_recording)."""
        mock_which.return_value = "/usr/bin/arecord"
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_wav:
            tmp_wav.write(b"RIFF" + b"\x00" * 2000)
            tmp_wav.flush()

            wav_path = self.mgr.start_recording(output_wav_path=tmp_wav.name)
            self.assertEqual(wav_path, tmp_wav.name)
            self.assertTrue(self.mgr.is_recording())

            with patch("os.killpg"):
                stopped = self.mgr.stop_recording()
                self.assertEqual(stopped, tmp_wav.name)
                self.assertFalse(self.mgr.is_recording())

    @patch("subprocess.run")
    def test_transcribe_mock(self, mock_run):
        """Verifica la invocación del worker para transcripción STT."""
        with patch.object(self.mgr, "is_venv_ready", return_value=True):
            with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_wav:
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_proc.stdout = json.dumps({"ok": True, "text": "hola mundo desde ddev studio"})
                mock_run.return_value = mock_proc

                text = self.mgr.transcribe(tmp_wav.name, language="es")
                self.assertEqual(text, "hola mundo desde ddev studio")

    @patch("subprocess.run")
    def test_synthesize_mock(self, mock_run):
        """Verifica la invocación del worker para síntesis TTS."""
        with patch.object(self.mgr, "is_venv_ready", return_value=True), \
             patch.object(self.mgr, "are_models_downloaded", return_value=True), \
             patch.object(self.mgr, "_daemon_synthesize", return_value=None):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps({"ok": True, "output": "/tmp/test.wav"})
            mock_run.return_value = mock_proc

            out = self.mgr.synthesize("Texto de prueba")
            self.assertEqual(out, "/tmp/test.wav")

    def test_clean_text_for_speech(self):
        """Verifica la limpieza de Markdown, código, URLs y emojis para voz."""
        from ddev_studio.core.voice import clean_text_for_speech

        raw_sample = (
            "# Título Principal\n\n"
            "¡Hola! **DDEV Studio** es genial.\n"
            "Ejecuta este comando:\n"
            "```bash\n"
            "ddev start\n"
            "```\n"
            "Visita [la web](https://ddev.com) para más info. 🚀"
        )
        cleaned = clean_text_for_speech(raw_sample)
        self.assertNotIn("```", cleaned)
        self.assertNotIn("#", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("https://ddev.com", cleaned)
        self.assertIn("ddev start", cleaned)
        self.assertIn("DDEV Studio es genial", cleaned)

    def test_split_into_speech_chunks(self):
        """Verifica la división inteligente de texto en oraciones digeribles."""
        from ddev_studio.core.voice import split_into_speech_chunks

        text = "Primera frase de saludo. Segunda frase con instrucciones técnicas. ¿Entendiste la explicación?"
        chunks = split_into_speech_chunks(text)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(any("Primera frase" in c for c in chunks))
        self.assertTrue(any("explicación" in c for c in chunks))

    def test_unload_daemon(self):
        """Verifica la descarga del demonio de RAM."""
        mock_proc = MagicMock()
        self.mgr._daemon_process = mock_proc
        self.mgr.unload_daemon()
        mock_proc.stdin.write.assert_called()
        self.assertIsNone(self.mgr._daemon_process)


if __name__ == "__main__":
    unittest.main()
