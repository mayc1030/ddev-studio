# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el catálogo canónico y resolvedor de herramientas
contextuales por framework (core/framework_tools.py).
"""

import os
import sys
import tempfile
import shutil
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.core.framework_tools import (
    FRAMEWORK_TOOLKITS,
    UNIVERSAL_TOOLS,
    get_framework_toolkit,
    get_universal_tools,
)


class TestFrameworkTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_framework_toolkits_catalog_integrity(self):
        expected_frameworks = ["laravel", "django", "wordpress", "symfony", "frontend", "php_generic", "python_generic"]
        for fw_id in expected_frameworks:
            self.assertIn(fw_id, FRAMEWORK_TOOLKITS)
            tk = FRAMEWORK_TOOLKITS[fw_id]
            self.assertIn("id", tk)
            self.assertIn("icon", tk)
            self.assertIn("title", tk)
            self.assertIn("desc", tk)
            self.assertIn("tools", tk)
            self.assertIsInstance(tk["tools"], list)
            self.assertGreater(len(tk["tools"]), 0)

            for tool in tk["tools"]:
                self.assertIn("id", tool)
                self.assertIn("label", tool)
                self.assertIn("cmd", tool)
                self.assertIn("type", tool)
                self.assertIn(tool["type"], ["progress", "terminal"])
                if tool["type"] == "progress":
                    self.assertTrue(isinstance(tool["cmd"], list) or isinstance(tool["cmd"], str))

    def test_universal_tools_integrity(self):
        tools = get_universal_tools()
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 3)
        tool_ids = [t["id"] for t in tools]
        self.assertIn("logs", tool_ids)
        self.assertIn("ssh", tool_ids)
        self.assertIn("describe", tool_ids)

        for t in tools:
            self.assertIn("id", t)
            self.assertIn("label", t)
            self.assertIn("cmd", t)
            self.assertIn("type", t)

    def test_resolve_laravel(self):
        # By tech_type
        tk = get_framework_toolkit("laravel")
        self.assertIsNotNone(tk)
        self.assertEqual(tk["id"], "laravel")
        tool_ids = [t["id"] for t in tk["tools"]]
        self.assertIn("migrate", tool_ids)
        self.assertIn("route_list", tool_ids)
        self.assertIn("tinker", tool_ids)

        # By artisan file heuristic
        artisan_file = os.path.join(self.test_dir, "artisan")
        with open(artisan_file, "w") as f:
            f.write("#!/usr/bin/env php")
        tk_file = get_framework_toolkit("php", self.test_dir)
        self.assertIsNotNone(tk_file)
        self.assertEqual(tk_file["id"], "laravel")

    def test_resolve_django(self):
        # By tech_type
        tk = get_framework_toolkit("django")
        self.assertIsNotNone(tk)
        self.assertEqual(tk["id"], "django")
        tool_ids = [t["id"] for t in tk["tools"]]
        self.assertIn("migrate", tool_ids)
        self.assertIn("createsuperuser", tool_ids)
        self.assertIn("collectstatic", tool_ids)
        self.assertIn("shell", tool_ids)

        # By manage.py file heuristic
        manage_file = os.path.join(self.test_dir, "manage.py")
        with open(manage_file, "w") as f:
            f.write("#!/usr/bin/env python")
        tk_file = get_framework_toolkit("python", self.test_dir)
        self.assertIsNotNone(tk_file)
        self.assertEqual(tk_file["id"], "django")

    def test_resolve_wordpress(self):
        tk = get_framework_toolkit("wordpress")
        self.assertIsNotNone(tk)
        self.assertEqual(tk["id"], "wordpress")
        tool_ids = [t["id"] for t in tk["tools"]]
        self.assertIn("cache_flush", tool_ids)
        self.assertIn("plugin_list", tool_ids)
        self.assertIn("core_update", tool_ids)
        self.assertIn("shell", tool_ids)

    def test_resolve_symfony(self):
        tk = get_framework_toolkit("symfony")
        self.assertIsNotNone(tk)
        self.assertEqual(tk["id"], "symfony")
        tool_ids = [t["id"] for t in tk["tools"]]
        self.assertIn("cache_clear", tool_ids)
        self.assertIn("doctrine_migrate", tool_ids)
        self.assertIn("debug_router", tool_ids)

    def test_resolve_frontend(self):
        for fe in ["next", "react", "vue", "angular"]:
            tk = get_framework_toolkit(fe)
            self.assertIsNotNone(tk)
            self.assertTrue("Frontend" in tk["title"] or fe.capitalize() in tk["title"])
            tool_ids = [t["id"] for t in tk["tools"]]
            self.assertIn("npm_install", tool_ids)
            self.assertIn("npm_build", tool_ids)

        # Heuristic package.json without composer.json
        pkg_file = os.path.join(self.test_dir, "package.json")
        with open(pkg_file, "w") as f:
            f.write("{}")
        tk_pkg = get_framework_toolkit("custom", self.test_dir)
        self.assertIsNotNone(tk_pkg)
        self.assertEqual(tk_pkg["id"], "frontend")

    def test_resolve_python_generic(self):
        tk_py = get_framework_toolkit("python")
        self.assertIsNotNone(tk_py)
        self.assertEqual(tk_py["id"], "python_generic")

        tk_flask = get_framework_toolkit("flask")
        self.assertIsNotNone(tk_flask)
        self.assertIn("Flask", tk_flask["title"])

    def test_resolve_php_generic_and_drupal_isolation(self):
        tk_php = get_framework_toolkit("php")
        self.assertIsNotNone(tk_php)
        self.assertEqual(tk_php["id"], "php_generic")

        # Drupal has its own studio, so it should not return php_generic
        tk_drupal = get_framework_toolkit("drupal")
        self.assertIsNone(tk_drupal)

        # composer.json in pure php project
        comp_file = os.path.join(self.test_dir, "composer.json")
        with open(comp_file, "w") as f:
            f.write("{}")
        tk_comp = get_framework_toolkit("custom", self.test_dir)
        self.assertIsNotNone(tk_comp)
        self.assertEqual(tk_comp["id"], "php_generic")

    def test_resolve_unknown(self):
        tk_none = get_framework_toolkit("static_html", self.test_dir)
        self.assertIsNone(tk_none)


if __name__ == "__main__":
    unittest.main()
