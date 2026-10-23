# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el módulo de herramientas SSL locales (ddev_studio.core.ssl_tools).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Asegurar que el directorio raíz esté en sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.core.ssl_tools import (
    is_mkcert_installed,
    is_certutil_installed,
    get_certutil_install_command,
    check_ssl_health,
    run_mkcert_install
)


class TestSslTools(unittest.TestCase):

    @patch("shutil.which")
    def test_is_mkcert_installed(self, mock_which):
        mock_which.return_value = "/usr/local/bin/mkcert"
        self.assertTrue(is_mkcert_installed())

        mock_which.return_value = None
        self.assertFalse(is_mkcert_installed())

    @patch("shutil.which")
    def test_is_certutil_installed(self, mock_which):
        mock_which.return_value = "/usr/bin/certutil"
        self.assertTrue(is_certutil_installed())

        mock_which.return_value = None
        self.assertFalse(is_certutil_installed())

    def test_get_certutil_install_command(self):
        cmd = get_certutil_install_command()
        self.assertIn("libnss3-tools", cmd)
        self.assertIn("apt", cmd)

    @patch("ddev_studio.core.ssl_tools.is_certutil_installed")
    @patch("ddev_studio.core.ssl_tools.is_mkcert_installed")
    def test_check_ssl_health_missing_mkcert(self, mock_mkcert, mock_certutil):
        mock_mkcert.return_value = False
        mock_certutil.return_value = True

        health = check_ssl_health()
        self.assertFalse(health["healthy"])
        self.assertEqual(health["status_code"], "missing_mkcert")
        self.assertFalse(health["mkcert_installed"])

    @patch("ddev_studio.core.ssl_tools.is_certutil_installed")
    @patch("ddev_studio.core.ssl_tools.is_mkcert_installed")
    def test_check_ssl_health_missing_certutil(self, mock_mkcert, mock_certutil):
        mock_mkcert.return_value = True
        mock_certutil.return_value = False

        health = check_ssl_health()
        self.assertFalse(health["healthy"])
        self.assertEqual(health["status_code"], "missing_certutil")
        self.assertTrue(health["mkcert_installed"])
        self.assertFalse(health["certutil_installed"])
        self.assertIn("libnss3-tools", health["recommendation"])

    @patch("ddev_studio.core.ssl_tools.is_certutil_installed")
    @patch("ddev_studio.core.ssl_tools.is_mkcert_installed")
    def test_check_ssl_health_all_ok(self, mock_mkcert, mock_certutil):
        mock_mkcert.return_value = True
        mock_certutil.return_value = True

        health = check_ssl_health()
        self.assertTrue(health["healthy"])
        self.assertEqual(health["status_code"], "ok")
        self.assertTrue(health["mkcert_installed"])
        self.assertTrue(health["certutil_installed"])

    @patch("ddev_studio.core.ssl_tools.is_mkcert_installed")
    def test_run_mkcert_install_not_installed(self, mock_mkcert):
        mock_mkcert.return_value = False
        success, msg = run_mkcert_install()
        self.assertFalse(success)
        self.assertIn("no se encuentra instalado", msg)

    @patch("subprocess.run")
    @patch("ddev_studio.core.ssl_tools.is_mkcert_installed")
    def test_run_mkcert_install_success(self, mock_mkcert, mock_run):
        mock_mkcert.return_value = True
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "The local CA is now installed in the trust store!"
        mock_res.stderr = ""
        mock_run.return_value = mock_res

        success, msg = run_mkcert_install()
        self.assertTrue(success)
        self.assertIn("The local CA is now installed", msg)

    @patch("subprocess.run")
    @patch("ddev_studio.core.ssl_tools.is_mkcert_installed")
    def test_run_mkcert_install_exception(self, mock_mkcert, mock_run):
        mock_mkcert.return_value = True
        mock_run.side_effect = OSError("Permission denied")

        success, msg = run_mkcert_install()
        self.assertFalse(success)
        self.assertIn("Permission denied", msg)


if __name__ == "__main__":
    unittest.main()
