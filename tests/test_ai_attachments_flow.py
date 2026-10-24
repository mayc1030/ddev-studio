# -*- coding: utf-8 -*-
"""
Pruebas exhaustivas para el flujo completo de archivos adjuntos (.md, código, logs)
y contexto universal en el Asistente de IA (ai_assistant.py & ai_client.py).
"""

import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.core.ai_client import (
    read_context_file,
    find_and_read_project_doc,
    SUPPORTED_TEXT_EXTENSIONS,
    MAX_CONTEXT_FILE_BYTES,
)
from ddev_studio.ui.views.ai_assistant import AIAssistantView


class TestAIAttachmentsFlow(unittest.TestCase):
    """Valida la carga y procesamiento de .md, código fuente y logs en el Asistente IA."""

    def setUp(self):
        self.view = AIAssistantView(main_app=None)

    def test_supported_extensions_completeness(self):
        """Verifica que las extensiones clave estén soportadas."""
        for ext in [".md", ".markdown", ".py", ".php", ".js", ".ts", ".json", ".yaml", ".yml", ".log", ".sql", ".sh"]:
            self.assertIn(ext, SUPPORTED_TEXT_EXTENSIONS)

    def test_load_markdown_file_and_create_chip(self):
        """Valida la carga de un archivo Markdown real y la generación del chip visual."""
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("# Arquitectura del Sistema\n\n- Componente A\n- Componente B\n")
            md_path = f.name

        try:
            # 1. Leer archivo
            file_data = read_context_file(md_path)
            self.assertEqual(file_data["name"], os.path.basename(md_path))
            self.assertFalse(file_data["truncated"])
            self.assertIn("Arquitectura del Sistema", file_data["content"])

            # 2. Adjuntar a la vista
            self.view._attach_file(md_path)
            self.assertEqual(len(self.view.attached_files), 1)
            self.assertTrue(self.view.attachments_scrolled.get_visible())

            # 3. Intentar adjuntar el mismo archivo (debe ignorarse por duplicado)
            self.view._attach_file(md_path)
            self.assertEqual(len(self.view.attached_files), 1)

            # 4. Quitar archivo
            chip = self.view.attachments_box.get_children()[0]
            self.view._remove_attachment(chip, self.view.attached_files[0])
            self.assertEqual(len(self.view.attached_files), 0)
            self.assertFalse(self.view.attachments_scrolled.get_visible())
        finally:
            if os.path.exists(md_path):
                os.remove(md_path)

    def test_load_source_code_and_logs(self):
        """Valida la carga de archivos de código Python y archivos de registro .log."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f_py:
            f_py.write("def calculate_metrics():\n    return {'cpu': 12.5, 'ram': '2GB'}\n")
            py_path = f_py.name

        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f_log:
            f_log.write("[ERROR] 2026-10-23 20:00:00 Connection to MariaDB timed out\n")
            log_path = f_log.name

        try:
            self.view._attach_file(py_path)
            self.view._attach_file(log_path)
            self.assertEqual(len(self.view.attached_files), 2)
            self.assertEqual(len(self.view.attachments_box.get_children()), 2)
        finally:
            if os.path.exists(py_path):
                os.remove(py_path)
            if os.path.exists(log_path):
                os.remove(log_path)

    def test_safe_truncation_large_file(self):
        """Valida que un archivo grande (> 30 KB) se trunque para proteger la CPU."""
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("# Plan Gigante\n" + ("x" * (MAX_CONTEXT_FILE_BYTES + 5000)))
            big_path = f.name

        try:
            data = read_context_file(big_path)
            self.assertTrue(data["truncated"])
            self.assertEqual(len(data["content"]), MAX_CONTEXT_FILE_BYTES)
            self.assertGreater(data["size_bytes"], MAX_CONTEXT_FILE_BYTES)
        finally:
            if os.path.exists(big_path):
                os.remove(big_path)

    def test_find_and_read_project_doc_case_variations(self):
        """Valida que detecte README.md, Readme.md o PROJECT_CONTEXT.md sin importar mayúsculas."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Caso 1: Readme.md
            readme_path = os.path.join(tmp_dir, "Readme.md")
            with open(readme_path, "w") as f:
                f.write("# Documentación del proyecto Readme\n")

            doc = find_and_read_project_doc(tmp_dir)
            self.assertIsNotNone(doc)
            self.assertEqual(doc["name"], "Readme.md")

            # Caso 2: PROJECT_CONTEXT.md (prioridad mayor)
            ctx_path = os.path.join(tmp_dir, "PROJECT_CONTEXT.md")
            with open(ctx_path, "w") as f:
                f.write("# Memoria viva del proyecto\n")

            doc2 = find_and_read_project_doc(tmp_dir)
            self.assertIsNotNone(doc2)
            self.assertEqual(doc2["name"], "PROJECT_CONTEXT.md")
            self.assertIn("Memoria viva", doc2["content"])


if __name__ == "__main__":
    unittest.main()
