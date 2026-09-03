# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el módulo de gestión del catálogo y Add-ons de DDEV (core/addons.py).
"""

import os
import sys
import tempfile
import shutil
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.core.addons import (
    FALLBACK_ADDONS,
    ADDON_CATEGORIES,
    KNOWN_ADDON_DESCRIPTIONS,
    get_addon_description,
    classify_addon_category,
    fetch_available_addons,
    get_installed_addons,
    is_addon_installed,
    build_install_addon_command,
    build_remove_addon_command
)


class TestAddonsCore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_fallback_addons_structure(self):
        self.assertIsInstance(FALLBACK_ADDONS, list)
        self.assertGreater(len(FALLBACK_ADDONS), 5)
        for addon in FALLBACK_ADDONS:
            self.assertIn("title", addon)
            self.assertIn("description", addon)
            self.assertIn("type", addon)
            self.assertIn("category", addon)
            self.assertIn("github_url", addon)

    def test_addon_categories(self):
        self.assertIsInstance(ADDON_CATEGORIES, list)
        cat_ids = [c["id"] for c in ADDON_CATEGORIES]
        self.assertIn("all", cat_ids)
        self.assertIn("official", cat_ids)
        self.assertIn("db_cache", cat_ids)
        self.assertIn("installed", cat_ids)

    def test_classify_addon_category(self):
        self.assertEqual(classify_addon_category("ddev/ddev-redis", "In-memory cache", "official"), "db_cache")
        self.assertEqual(classify_addon_category("ddev/ddev-solr", "Search engine for Drupal", "official"), "search")
        self.assertEqual(classify_addon_category("ddev/ddev-browsersync", "Live CSS reload", "official"), "frontend_dx")
        self.assertEqual(classify_addon_category("ddev/ddev-cron", "Cron runner", "official"), "devops")
        self.assertEqual(classify_addon_category("ddev/ddev-selenium-standalone-chrome", "Testing with chrome", "official"), "testing")

    def test_is_addon_installed(self):
        installed = ["redis", "ddev-solr", "ddev/ddev-cron"]
        self.assertTrue(is_addon_installed("ddev/ddev-redis", installed))
        self.assertTrue(is_addon_installed("ddev/ddev-solr", installed))
        self.assertTrue(is_addon_installed("ddev/ddev-cron", installed))
        self.assertFalse(is_addon_installed("ddev/ddev-mongo", installed))
        self.assertFalse(is_addon_installed("ddev/ddev-elasticsearch", []))

    def test_detect_installed_addons_from_fs(self):
        # Empty dir
        self.assertEqual(get_installed_addons(self.test_dir), [])

        # Create .ddev/docker-compose.redis.yaml
        ddev_dir = os.path.join(self.test_dir, ".ddev")
        os.makedirs(ddev_dir, exist_ok=True)
        with open(os.path.join(ddev_dir, "docker-compose.redis.yaml"), "w") as f:
            f.write("# Redis compose\n")

        # Create .ddev/addon-metadata/ddev-cron
        meta_dir = os.path.join(ddev_dir, "addon-metadata", "ddev-cron")
        os.makedirs(meta_dir, exist_ok=True)

        installed = get_installed_addons(self.test_dir)
        self.assertTrue(is_addon_installed("ddev/ddev-redis", installed))
        self.assertTrue(is_addon_installed("ddev/ddev-cron", installed))
        self.assertFalse(is_addon_installed("ddev/ddev-solr", installed))

    def test_build_commands(self):
        cmd_in = build_install_addon_command("ddev/ddev-redis")
        self.assertEqual(cmd_in, ["ddev", "get", "ddev/ddev-redis"])

        cmd_rm = build_remove_addon_command("ddev/ddev-redis")
        self.assertEqual(cmd_rm, ["ddev", "get", "--remove", "ddev/ddev-redis"])

    def test_get_addon_description(self):
        desc_redis = get_addon_description("ddev/ddev-redis", "")
        self.assertIn("Redis", desc_redis)
        self.assertIn("caché", desc_redis)

        desc_cron = get_addon_description("ddev/ddev-cron", "some raw desc")
        self.assertIn("cron", desc_cron.lower())

        desc_unknown = get_addon_description("someuser/ddev-custom-tool", "Descripcion personalizada")
        self.assertEqual(desc_unknown, "Descripcion personalizada")


if __name__ == "__main__":
    unittest.main()
