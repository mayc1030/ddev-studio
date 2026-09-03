# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el módulo de herramientas y APIs de Drupal (drupal_tools.py).
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.core.drupal_tools import (
    sanitize_machine_name,
    scan_custom_modules,
    scan_custom_themes,
    parse_pm_list_output,
    build_drush_generate_command
)


class TestDrupalTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sanitize_machine_name(self):
        self.assertEqual(sanitize_machine_name("Mi Módulo Especial"), "mi_m_dulo_especial")
        self.assertEqual(sanitize_machine_name("custom-feature-123"), "custom_feature_123")
        self.assertEqual(sanitize_machine_name("___leading_and_trailing___"), "leading_and_trailing")
        self.assertEqual(sanitize_machine_name("special@#chars"), "special_chars")
        self.assertEqual(sanitize_machine_name(""), "")

    def test_scan_custom_modules(self):
        # Empty dir
        self.assertEqual(scan_custom_modules(self.test_dir, "web"), [])

        # Create module inside web/modules/custom
        mod_dir = os.path.join(self.test_dir, "web", "modules", "custom", "my_custom_mod")
        os.makedirs(mod_dir, exist_ok=True)
        with open(os.path.join(mod_dir, "my_custom_mod.info.yml"), "w") as f:
            f.write("name: My Custom Mod\ntype: module\ncore_version_requirement: ^10 || ^11\n")

        mods = scan_custom_modules(self.test_dir, "web")
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0]["name"], "my_custom_mod")
        self.assertIn("my_custom_mod.info.yml", os.listdir(mods[0]["path"]))

    def test_scan_custom_themes(self):
        # Empty dir
        self.assertEqual(scan_custom_themes(self.test_dir, "web"), [])

        # Create theme inside web/themes/custom
        thm_dir = os.path.join(self.test_dir, "web", "themes", "custom", "my_custom_theme")
        os.makedirs(thm_dir, exist_ok=True)
        with open(os.path.join(thm_dir, "my_custom_theme.info.yml"), "w") as f:
            f.write("name: My Custom Theme\ntype: theme\ncore_version_requirement: ^10 || ^11\n")

        themes = scan_custom_themes(self.test_dir, "web")
        self.assertEqual(len(themes), 1)
        self.assertEqual(themes[0]["name"], "my_custom_theme")

    def test_parse_pm_list_output_json(self):
        raw_json = json.dumps({
            "metatag": {"status": "Enabled", "type": "module"},
            "pathauto": {"status": "Enabled", "type": "module"},
            "token": {"status": "Enabled", "type": "module"},
            "simple_sitemap": {"status": "Enabled", "type": "module"},
            "redirect": {"status": "Enabled", "type": "module"},
            "paragraphs": {"status": "Enabled", "type": "module"},
            "field_group": {"status": "Enabled", "type": "module"},
            "admin_toolbar": {"status": "Enabled", "type": "module"},
            "focal_point": {"status": "Enabled", "type": "module"},
            "svg_image": {"status": "Enabled", "type": "module"},
            "jsonapi": {"status": "Enabled", "type": "module"},
            "jsonapi_extras": {"status": "Enabled", "type": "module"},
            "rest": {"status": "Disabled", "type": "module"},
            "simple_oauth": {"status": "Enabled", "type": "module"},
            "graphql": {"status": "Enabled", "type": "module"},
            "devel": {"status": "Enabled", "type": "module"},
            "devel_php": {"status": "Enabled", "type": "module"},
            "stage_file_proxy": {"status": "Enabled", "type": "module"}
        })
        res = parse_pm_list_output(raw_json)
        self.assertTrue(res["metatag"])
        self.assertTrue(res["pathauto"])
        self.assertTrue(res["paragraphs"])
        self.assertTrue(res["admin_toolbar"])
        self.assertTrue(res["focal_point"])
        self.assertTrue(res["jsonapi"])
        self.assertTrue(res["jsonapi_extras"])
        self.assertFalse(res["rest"])
        self.assertTrue(res["simple_oauth"])
        self.assertTrue(res["graphql"])
        self.assertTrue(res["devel"])
        self.assertTrue(res["devel_php"])
        self.assertTrue(res["stage_file_proxy"])

    def test_parse_pm_list_output_text(self):
        raw_text = """
        Package   Name                   Status   Version
        SEO       Metatag                Enabled  2.0.0
        SEO       Pathauto               Enabled  1.12.0
        SEO       Token                  Enabled  1.14.0
        SEO       Simple XML Sitemap     Enabled  4.1.0
        Structure Paragraphs             Enabled  1.16.0
        Structure Field Group            Enabled  3.4.0
        Admin     Admin Toolbar          Enabled  3.4.0
        Media     Focal Point            Enabled  2.1.0
        Core      JSON:API               Enabled  10.3.0
        Core      REST                   Disabled 10.3.0
        Web       Simple OAuth           Enabled  5.2.0
        Devel     Devel                  Enabled  5.1.0
        Devel     Devel PHP              Enabled  1.2.0
        Dev       Stage File Proxy       Enabled  2.1.0
        """
        res = parse_pm_list_output(raw_text)
        self.assertTrue(res["metatag"])
        self.assertTrue(res["pathauto"])
        self.assertTrue(res["paragraphs"])
        self.assertTrue(res["admin_toolbar"])
        self.assertTrue(res["focal_point"])
        self.assertTrue(res["jsonapi"])
        self.assertFalse(res["rest"])
        self.assertTrue(res["simple_oauth"])
        self.assertTrue(res["devel"])
        self.assertTrue(res["devel_php"])
        self.assertTrue(res["stage_file_proxy"])

    def test_parse_pm_list_empty(self):
        res = parse_pm_list_output("")
        for k, v in res.items():
            self.assertFalse(v)

    def test_build_drush_generate_command(self):
        # Without answers
        cmd1 = build_drush_generate_command("module")
        self.assertEqual(cmd1, ["ddev", "drush", "generate", "module"])

        # With answers
        answers = {"name": "Test", "machine_name": "test"}
        cmd2 = build_drush_generate_command("controller", answers)
        self.assertEqual(cmd2[0], "ddev")
        self.assertEqual(cmd2[1], "drush")
        self.assertEqual(cmd2[2], "generate")
        self.assertEqual(cmd2[3], "controller")
        self.assertTrue(cmd2[4].startswith("--answers="))
        self.assertIn('"machine_name": "test"', cmd2[4])


if __name__ == "__main__":
    unittest.main()
