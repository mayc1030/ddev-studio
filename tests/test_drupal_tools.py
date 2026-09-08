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
    build_drush_generate_command,
    build_starterkit_theme_command,
    build_subtheme_command,
    is_theme_installed,
    DRUPAL_BASE_THEMES_PRESETS,
    scaffold_custom_module,
    scaffold_custom_theme,
    scaffold_custom_component,
    scaffold_rest_resource
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
            "entity_usage": {"status": "Enabled", "type": "module"},
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
        self.assertTrue(res["entity_usage"])
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
        Structure Entity Usage           Enabled  2.0.0
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
        self.assertTrue(res["entity_usage"])
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

    def test_build_starterkit_theme_command(self):
        cmd = build_starterkit_theme_command("my_theme", "My Theme", "web")
        self.assertEqual(cmd[0], "ddev")
        self.assertEqual(cmd[1], "exec")
        self.assertEqual(cmd[2], "bash")
        self.assertEqual(cmd[3], "-c")
        self.assertIn("vendor/bin/dr generate-theme my_theme", cmd[4])
        self.assertIn("web/core/scripts/drupal generate-theme my_theme", cmd[4])
        self.assertIn("--path=themes/custom", cmd[4])
        self.assertIn("drush cr", cmd[4])

    def test_scaffold_custom_module(self):
        files = scaffold_custom_module(
            self.test_dir, "web", "my_test_mod", "My Test Mod",
            "Modulo de prueba", "Custom", has_install=True, has_permissions=True
        )
        self.assertEqual(len(files), 4)
        mod_dir = os.path.join(self.test_dir, "web", "modules", "custom", "my_test_mod")
        self.assertTrue(os.path.isfile(os.path.join(mod_dir, "my_test_mod.info.yml")))
        self.assertTrue(os.path.isfile(os.path.join(mod_dir, "my_test_mod.module")))
        self.assertTrue(os.path.isfile(os.path.join(mod_dir, "my_test_mod.install")))
        self.assertTrue(os.path.isfile(os.path.join(mod_dir, "my_test_mod.permissions.yml")))

        with open(os.path.join(mod_dir, "my_test_mod.info.yml")) as f:
            content = f.read()
        self.assertIn("name: 'My Test Mod'", content)
        self.assertIn("core_version_requirement:", content)

    def test_scaffold_custom_theme(self):
        files = scaffold_custom_theme(
            self.test_dir, "web", "my_custom_theme", "My Custom Theme", "olivero"
        )
        self.assertEqual(len(files), 5)
        thm_dir = os.path.join(self.test_dir, "web", "themes", "custom", "my_custom_theme")
        self.assertTrue(os.path.isfile(os.path.join(thm_dir, "my_custom_theme.info.yml")))
        self.assertTrue(os.path.isfile(os.path.join(thm_dir, "my_custom_theme.theme")))
        self.assertTrue(os.path.isfile(os.path.join(thm_dir, "my_custom_theme.libraries.yml")))
        self.assertTrue(os.path.isfile(os.path.join(thm_dir, "css", "style.css")))
        self.assertTrue(os.path.isfile(os.path.join(thm_dir, "js", "script.js")))

    def test_scaffold_custom_component(self):
        # Create module first
        scaffold_custom_module(self.test_dir, "web", "demo_mod", "Demo Mod")
        # Scaffold controller
        files = scaffold_custom_component(self.test_dir, "web", "demo_mod", "controller", "HelloController")
        self.assertEqual(len(files), 2)
        ctrl_path = os.path.join(self.test_dir, "web", "modules", "custom", "demo_mod", "src", "Controller", "HelloController.php")
        self.assertTrue(os.path.isfile(ctrl_path))
        routing_path = os.path.join(self.test_dir, "web", "modules", "custom", "demo_mod", "demo_mod.routing.yml")
        self.assertTrue(os.path.isfile(routing_path))

    def test_scaffold_rest_resource(self):
        scaffold_custom_module(self.test_dir, "web", "api_mod", "API Mod")
        files = scaffold_rest_resource(self.test_dir, "web", "api_mod", "products_api", "Products API", "/api/v1/products")
        self.assertEqual(len(files), 1)
        res_path = os.path.join(self.test_dir, "web", "modules", "custom", "api_mod", "src", "Plugin", "rest", "resource", "ProductsApiResource.php")
        self.assertTrue(os.path.isfile(res_path))
        with open(res_path) as f:
            code = f.read()
        self.assertIn("@RestResource", code)
        self.assertIn("class ProductsApiResource extends ResourceBase", code)

    def test_drupal_base_themes_presets(self):
        self.assertIn("olivero", DRUPAL_BASE_THEMES_PRESETS)
        self.assertIn("bootstrap5", DRUPAL_BASE_THEMES_PRESETS)
        self.assertIn("bootstrap_barrio", DRUPAL_BASE_THEMES_PRESETS)
        self.assertIn("radix", DRUPAL_BASE_THEMES_PRESETS)
        self.assertIn("gin", DRUPAL_BASE_THEMES_PRESETS)
        self.assertIn("claro", DRUPAL_BASE_THEMES_PRESETS)
        self.assertIn("bartik", DRUPAL_BASE_THEMES_PRESETS)
        self.assertEqual(DRUPAL_BASE_THEMES_PRESETS["bootstrap5"]["composer_pkg"], "drupal/bootstrap5")
        self.assertEqual(DRUPAL_BASE_THEMES_PRESETS["gin"]["type"], "admin")

    def test_is_theme_installed(self):
        # Empty dir
        self.assertFalse(is_theme_installed(self.test_dir, "web", "bootstrap5"))

        # Core theme in web/core/themes/olivero
        olivero_dir = os.path.join(self.test_dir, "web", "core", "themes", "olivero")
        os.makedirs(olivero_dir, exist_ok=True)
        self.assertTrue(is_theme_installed(self.test_dir, "web", "olivero"))

        # Contrib theme in web/themes/contrib/bootstrap5
        b5_dir = os.path.join(self.test_dir, "web", "themes", "contrib", "bootstrap5")
        os.makedirs(b5_dir, exist_ok=True)
        self.assertTrue(is_theme_installed(self.test_dir, "web", "bootstrap5"))

        # Theme defined in composer.json
        composer_file = os.path.join(self.test_dir, "composer.json")
        with open(composer_file, "w", encoding="utf-8") as f:
            json.dump({"require": {"drupal/bootstrap_barrio": "^5.5"}}, f)
        self.assertTrue(is_theme_installed(self.test_dir, "web", "bootstrap_barrio"))

    def test_scaffold_custom_theme_presets(self):
        # Scaffold Bootstrap 5 subtheme
        files = scaffold_custom_theme(
            self.test_dir, "web", "b5_subtheme", "B5 Subtheme", "bootstrap5"
        )
        self.assertGreaterEqual(len(files), 5)
        info_path = os.path.join(self.test_dir, "web", "themes", "custom", "b5_subtheme", "b5_subtheme.info.yml")
        with open(info_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("base theme: 'bootstrap5'", content)
        self.assertIn("nav_branding: 'Navigation Branding'", content)
        self.assertIn("nav_main: 'Main Navigation'", content)

        lib_path = os.path.join(self.test_dir, "web", "themes", "custom", "b5_subtheme", "b5_subtheme.libraries.yml")
        with open(lib_path, "r", encoding="utf-8") as f:
            lib_content = f.read()
        self.assertIn("bootstrap5/global-styling", lib_content)

        # Scaffold Gin admin subtheme
        files_gin = scaffold_custom_theme(
            self.test_dir, "web", "gin_subtheme", "Gin Subtheme", "gin"
        )
        info_gin_path = os.path.join(self.test_dir, "web", "themes", "custom", "gin_subtheme", "gin_subtheme.info.yml")
        with open(info_gin_path, "r", encoding="utf-8") as f:
            gin_content = f.read()
        self.assertIn("base theme: 'gin'", gin_content)
        self.assertIn("pre_content: 'Pre-content'", gin_content)

    def test_build_subtheme_command(self):
        # Frontend theme with composer install and set default
        cmd1 = build_subtheme_command(
            machine_name="my_subtheme",
            base_theme="bootstrap5",
            composer_pkg="drupal/bootstrap5",
            install_base=True,
            enable_theme=True,
            set_as_default=True,
            is_admin_theme=False
        )
        self.assertEqual(cmd1[0], "ddev")
        self.assertEqual(cmd1[1], "exec")
        self.assertEqual(cmd1[2], "bash")
        self.assertEqual(cmd1[3], "-c")
        self.assertIn("composer require 'drupal/bootstrap5'", cmd1[4])
        self.assertIn("drush theme:enable bootstrap5 -y", cmd1[4])
        self.assertIn("drush theme:enable my_subtheme -y", cmd1[4])
        self.assertIn("drush config-set system.theme default my_subtheme -y", cmd1[4])
        self.assertIn("drush cr", cmd1[4])

        # Admin theme without composer install
        cmd2 = build_subtheme_command(
            machine_name="admin_subtheme",
            base_theme="gin",
            composer_pkg="drupal/gin",
            install_base=False,
            enable_theme=True,
            set_as_default=True,
            is_admin_theme=True
        )
        self.assertNotIn("composer require", cmd2[4])
        self.assertIn("drush theme:enable admin_subtheme -y", cmd2[4])
        self.assertIn("drush config-set system.theme admin admin_subtheme -y", cmd2[4])


if __name__ == "__main__":
    unittest.main()
