# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el cliente de IA Local (core/ai_client.py).
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.core.ai_client import (
    OllamaClient,
    CATALOG_RECOMMENDED_MODELS,
    DEFAULT_OLLAMA_URL
)


class TestAIAssistantCore(unittest.TestCase):

    def setUp(self):
        self.client = OllamaClient()

    def test_catalog_recommended_models_structure(self):
        self.assertIsInstance(CATALOG_RECOMMENDED_MODELS, list)
        self.assertGreaterEqual(len(CATALOG_RECOMMENDED_MODELS), 4)
        for m in CATALOG_RECOMMENDED_MODELS:
            self.assertIn("name", m)
            self.assertIn("label", m)
            self.assertIn("tagline", m)
            self.assertIn("size_str", m)
            self.assertIn("ram_req", m)

    def test_client_init(self):
        self.assertEqual(self.client.base_url, DEFAULT_OLLAMA_URL)
        custom_client = OllamaClient("http://192.168.1.50:11434")
        self.assertEqual(custom_client.base_url, "http://192.168.1.50:11434")

    def test_commands(self):
        install_cmd = " ".join(self.client.get_install_command())
        self.assertIn("curl", install_cmd)
        self.assertIn("ollama", install_cmd)

        install_nopk = self.client.get_install_command(use_pkexec=False)
        self.assertEqual(install_nopk[0], "bash")
        self.assertIn("curl", install_nopk[2])

        start_cmd = " ".join(self.client.get_start_command())
        self.assertIn("ollama", start_cmd)

    @patch("shutil.which")
    def test_is_binary_installed(self, mock_which):
        mock_which.return_value = "/usr/local/bin/ollama"
        self.assertTrue(self.client.is_binary_installed())

        mock_which.return_value = None
        self.assertFalse(self.client.is_binary_installed())

    @patch("urllib.request.urlopen")
    def test_is_server_running_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.getcode.return_value = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        self.assertTrue(self.client.is_server_running())

    @patch("urllib.request.urlopen")
    def test_is_server_running_failure(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        self.assertFalse(self.client.is_server_running())

    @patch("urllib.request.urlopen")
    def test_list_installed_models_success(self, mock_urlopen):
        fake_data = {
            "models": [
                {
                    "name": "llama3.2:3b",
                    "size": 2147483648,
                    "modified_at": "2026-09-01T12:00:00Z"
                },
                {
                    "name": "qwen2.5-coder:1.5b",
                    "size": 1048576000,
                    "modified_at": "2026-09-02T12:00:00Z"
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = json.dumps(fake_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        models = self.client.list_installed_models()
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["name"], "llama3.2:3b")
        self.assertIn("GB", models[0]["size_str"])
        self.assertEqual(models[1]["name"], "qwen2.5-coder:1.5b")

    @patch("urllib.request.urlopen")
    def test_list_installed_models_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Server down")
        models = self.client.list_installed_models()
        self.assertEqual(models, [])

    @patch("urllib.request.urlopen")
    def test_chat_stream_success(self, mock_urlopen):
        line1 = json.dumps({"message": {"content": "Hola, "}, "done": False}).encode("utf-8") + b"\n"
        line2 = json.dumps({"message": {"content": "soy tu IA local."}, "done": True}).encode("utf-8") + b"\n"

        mock_resp = MagicMock()
        mock_resp.__iter__.return_value = iter([line1, line2])
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        chunks = []
        messages = [{"role": "user", "content": "Hola"}]
        full_res = self.client.chat_stream("llama3.2:3b", messages, chunk_callback=chunks.append)

        self.assertEqual(chunks, ["Hola, ", "soy tu IA local."])
        self.assertEqual(full_res, "Hola, soy tu IA local.")

    @patch("urllib.request.urlopen")
    def test_chat_stream_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        chunks = []
        messages = [{"role": "user", "content": "Hola"}]
        full_res = self.client.chat_stream("llama3.2:3b", messages, chunk_callback=chunks.append)
        self.assertIn("Error", full_res)
        self.assertTrue(any("Error" in c for c in chunks))

    @patch("urllib.request.urlopen")
    def test_pull_model_stream(self, mock_urlopen):
        line1 = json.dumps({"status": "downloading", "completed": 500, "total": 1000}).encode("utf-8") + b"\n"
        line2 = json.dumps({"status": "success"}).encode("utf-8") + b"\n"

        mock_resp = MagicMock()
        mock_resp.__iter__.return_value = iter([line1, line2])
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        progress_events = []
        success = self.client.pull_model_stream("llama3.2:3b", progress_callback=progress_events.append)
        self.assertTrue(success)
        self.assertEqual(len(progress_events), 2)
        self.assertEqual(progress_events[0]["status"], "downloading")
        self.assertEqual(progress_events[1]["status"], "success")


if __name__ == "__main__":
    unittest.main()
